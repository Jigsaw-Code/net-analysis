# Copyright 2019 Jigsaw Operations LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -u

# Curl Errors (from `man libcurl-errors`)
declare -ir CURLE_OK=0
declare -ir CURLE_COULDNT_CONNECT=7  # We get this for connection refused.
declare -ir CURLE_OPERATION_TIMEDOUT=28
declare -ir CURLE_SSL_CONNECT_ERROR=35
declare -ir CURLE_PEER_FAILED_VERIFICATION=51
declare -ir CURLE_GOT_NOTHING=52  # Injected FIN triggers this.
declare -ir CURLE_RECV_ERROR=56  # We get this for connection reset by peer.
declare -ir CURLE_SSL_CACERT=60  # Could be MITM.

function is_online() {
  # Test signal
  local response
  # The gstatic.com url will return status 204 and no body.
  # It's HTTP so captive portals can intercept with a login page.
  response=$(curl --silent --dump-header - http://connectivitycheck.gstatic.com/generate_204 2> /dev/null)
  if (($? != 0)); then return 2; fi
  # Test captive portal
  local status=$(echo $response | head -1 | cut -d' ' -f 2)
  ((status == "204"))
}

# The HTTP test works by connecting to a well-behaved baseline that always returns the same output
# on invalid hostname. We then compare the output for our test domain and a domain we know
# is invalid. If the result changes, then we know there was injection.
function test_http_blocking() {
  local domain=$1
  # TODO: use a domain we control instead of example.com, which may change without notice.
  local http_response
  http_response=$(curl --silent --show-error --max-time 5 --connect-to ::example.com: http://$domain/ 2>&1)
  local http_result=$?
  if ((http_result == CURLE_OK)); then 
    local expected_reponse=$(curl --silent --show-error --max-time 5 --connect-to ::example.com: http://inexistent.example.com/ 2>&1)
    if diff <(echo "$http_response") <(echo "$expected_reponse") > /dev/null; then
      echo HTTP:OK Got expected response
    else
      echo HTTP:INTERFERENCE Got injected response
      diff <(echo "$http_response") <(echo "$expected_reponse")
    fi
  elif ((http_result == CURLE_GOT_NOTHING)); then
    echo "HTTP:INTERFERENCE Unexpected empty response when Host is $domain($http_response)"
  elif ((http_result == CURLE_RECV_ERROR)); then
    echo "HTTP:INTERFERENCE Cannot from established connection when Host is $domain($http_response)"
  elif ((http_result == CURLE_OPERATION_TIMEDOUT)); then
    echo "HTTP:LIKELY_INTERFERENCE Unexpected time out when Host is $domain ($http_response)"
  elif ((http_result == CURLE_COULDNT_CONNECT)); then
    echo "HTTP:INCONCLUSIVE Failed to connect to innocuous domain ($http_response)"
  else
    # TODO: Find out what errors are guaranteed blocking.
    echo "HTTP:INCONCLUSIVE Failed to fetch test domain from innocuous domain ($http_response)"
  fi
}

# The test for SNI-triggered blocking works by connecting to a well-behaved TLS server we know
# and checking if we can get a ServerHello back when presenting the test domain. If we
# get a response without a ServerHello, which may be empty or a reset, we know it's blocked.
# If we get a ServerHello and the CA chain is valid, then we know there was no injection and
# can conclude there's no blocking.
function test_sni_blocking() {
  local domain=$1
  # The `local` call will override `#?`, so we don't assign on the declaration.
  local curl_error
  curl_error=$(curl --silent --show-error --max-time 5 --connect-to ::example.com: "https://$domain/" 2>&1 >/dev/null)
  curl_result=$?
  if ((curl_result == CURLE_PEER_FAILED_VERIFICATION || curl_result == CURLE_OK)); then 
    echo "SNI:OK Got TLS ServerHello"
  elif ((curl_result == CURLE_SSL_CACERT)) && \
       [[ "$curl_error" =~ "no alternative certificate subject name matches target host name" ]]; then
    # On Linux curl outputs CURLE_SSL_CACERT for invalid subject name 🤷.
    echo "SNI:OK Got TLS ServerHello"
  elif ((curl_result == CURLE_GOT_NOTHING)); then
    echo "SNI:INTERFERENCE Unexpected empty response when SNI is $domain ($curl_error)"
  elif ((curl_result == CURLE_SSL_CONNECT_ERROR)); then
    echo "SNI:LIKELY_INTERFERENCE Unexpected TLS error when SNI is $domain ($curl_error)"
  else
    # TODO: Check for invalid CA chain: that indicates the server is misconfigured or
    # there's MITM going on.
    # TODO: Figure out what errors are guaranteed blocking.
    echo "SNI:INCONCLUSIVE Failed to get TLS ServerHello ($curl_error)"
  fi
}

# Test for DNS injection.
# It queries a root nameserver for the domain and expects a response with
# NOERROR, no answers and the list of nameservers for the domain's TLD.
# This method is superior to sending the query to a blackhole because
# it can provide positive confirmation that the query was not discarded.
# It relies on the high capacity and availability of the root nameservers
# and the fact that they are not blockable due to substantial collateral damage.
function test_dns_injection() {
  declare -r domain=$1
  declare -r root_nameserver=$(dig +short . ns | head -1)
  if [[ -z "$root_nameserver" ]]; then
    echo DNS_INJECTION:INCONCLUSIVE "Could not get root nameserver"
    return 2
  fi
  declare response
  if ! response=$(dig +time=2 @$root_nameserver $domain); then
    echo DNS_INJECTION:INTERFERENCE "Could not get response"
    return 1
  fi
  declare -r status=$(echo $response | grep -oE 'status: \w+' | cut -d ' ' -f 2)
  declare -ri num_answers=$(echo $response | grep -oE 'ANSWER: \w+' | cut -d ' ' -f 2)
  declare -ri num_auth=$(echo $response | grep -oE 'AUTHORITY: \w+' | cut -d ' ' -f 2)
  if [[ $status == 'NOERROR' && $num_answers == 0 && $num_auth -ge 1 ]]; then
    echo DNS_INJECTION:OK "Received expected response"
    return 0
  fi
  echo DNS_INJECTION:INTERFERENCE "Received unexpected response: $response"
  return 1
}

# Tests DNS interference. First tries to detect injection. If no injection,
# also tests the system resolver and verify whether the returned IPs are valid for
# the test domain.
function test_dns_blocking() {
  local domain=$1
  test_dns_injection $domain
  if [[ $? == 1 ]]; then
    # There's no point in testing the system resolver if we know reponses are injected.
    return
  fi

  declare -r ips=$(dig +dnssec +short $domain |  grep -o -E '([0-9]+\.){3}[0-9]+' | sort)
  declare -r ip_result=$(test_ips "$ips" "$domain")
  case $(echo $ip_result | cut -d\  -f 1) in
    IP_INVALID)
      echo SYSTEM_RESOLVER:INTERFERENCE $ip_result
      ;;
    IP_VALID)
      echo SYSTEM_RESOLVER:OK $ip_result
      ;;
    *)
      echo SYSTEM_RESOLVER:INCONCLUSIVE $ip_result
  esac
}

# Tests if IPs are valid for a given domain.
# We first check if it's a globally addressable IP (not localhost, local network etc.)
# Then we query Google DoH to get the IPs and use that as ground truth. If there's
# overlap, we conclude the IPs are valid.
# That may fail for load or geo balanced servers. In that case they will likely support
# HTTPS. If the IP can successfuly establish a TLS connection for the domain, that's proof
# the IP is valid for the domain.
# The (ip, domain) validation is vulnerable to censorship (IP and SNI-based blocking), but
# it does not have to happen at the test network. We could provide a backend for that instead.
function test_ips() {
  local ips=$1
  local domain=$2
  if [[ $ips == "" ]]; then
    echo IP_INVALID Did not get any IPs from DNS resolver
    return
  fi
  local ip=$(echo "$ips" | head -1)
  local ip_info=$(curl --silent "https://ipinfo.io/$ip")
  if echo "$ip_info" | grep "bogon" > /dev/null; then
    echo IP_INVALID IP $ip is bogus
    return
  fi

  # Validate IPs by comparing to a trusted resolution.
  # Hardcode IP address to bypass potential DNS blocking.
  # dns.google.com may still be blocked by IP or SNI. We use upper case domain to bypass some SNI blocking.
  # TODO: Check if dns.google.com is IP or SNI blocked.
  # TODO: Use ClientHello split to avoid more SNI blocking.
  # TODO: Run a DoH server for measurements on a shared IP address.
  # TODO: Recurse in case of blocking. That would still be vulnerable to blocked authoritatives.
  local ips_from_doh=$(curl --silent --connect-to ::8.8.8.8: https://DNS.GOOGLE/resolve?name=$domain |  grep -o -E '([0-9]+\.){3}[0-9]+' | sort)
  local common_ips=$(comm -12 <(echo "$ips") <(echo "$ips_from_doh"))
  if (( $(echo "$common_ips" | wc -w) > 0)); then
    echo IP_VALID Resolved IPs [$common_ips] were found on dns.google.com using DNS-over-HTTPS
    return
  fi

  # Validate IPs by establishing a TLS connection.
  # Upper case domain may bypass SNI censorship, reducing inconclusive cases.
  local upper_domain=$(echo $domain | tr [:lower:] [:upper:])
  local curl_error
  curl_error=$(curl --silent --show-error --connect-to ::$ip: https://$upper_domain/ 2>&1 > /dev/null) 
  local result=$?
  if ((result == CURLE_OK)) ; then
    echo "IP_VALID Resolved IP $ip can produce certificate for domain $domain"
    return
  elif ((result == CURLE_PEER_FAILED_VERIFICATION)); then
    echo "IP_INVALID IP $ip cannot produce domain certificate"
    return
  else
    echo "IP_INCONCLUSIVE Could not validate ips [$ips]. TLS test failed ($curl_error)"
    return
  fi
  # Other tests to try:
  # - Recurse with dnssec and qname minimization
}

function main() {
  date -u
  if ! is_online; then
    echo "You are offline"
    return 1
  fi
  local domain=$1
  echo YOUR NETWORK
  curl https://ipinfo.io
  echo

  printf "\nYOUR DNS RESOLVER\n"
  curl https://ipinfo.io/$(dig +short TXT whoami.ds.akahelp.net | grep ns | cut -d\" -f 4)
  echo

  printf "\nTESTS\n"
  test_http_blocking $domain
  test_sni_blocking $domain
  test_dns_blocking $domain

  # TODO: Test IP blocking
}

main $1
