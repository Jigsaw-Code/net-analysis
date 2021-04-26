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

function print_client_info() {
  declare -r client_info="$(curl --silent https://ipinfo.io |  sed 's/ *"\(.*\)": "\(.*\)",$/\1: \2/')"
  echo client_country: $(echo "$client_info" | grep '^country:' | cut -d' ' -f 2-)
  echo client_as: $(echo "$client_info" | grep '^org:' | cut -d' ' -f 2-)
}

# Test for DNS injection.
# It queries a root nameserver for the domain and expects a response with
# NOERROR, no answers and the list of nameservers for the domain's TLD.
# This method is superior to sending the query to a blackhole because
# it can provide positive confirmation that the query was not discarded.
# It relies on the high capacity and availability of the root nameservers
# and the fact that they are not blockable due to substantial collateral damage.
# TODO: Test TCP and upper case.
function test_dns_injection() {
  echo "DNS_INJECTION"
  declare -r domain=$1
  declare -r root_nameserver=$(dig +short . ns | head -1)
  if [[ -z "$root_nameserver" ]]; then
    echo "  root_nameserver_error: Could not get root nameserver"
    echo "  analysis: INCONCLUSIVE - Could not run test"
    return 2
  fi
  echo "  root_nameserver: $root_nameserver"
  declare response
  if ! response=$(dig +time=2 @$root_nameserver $domain); then
    echo "  query_error: Could not get response"
    echo "  analysis: INTERFERENCE - Could not get response"
    return 1
  fi
  declare -r status=$(echo $response | grep -oE 'status: \w+' | cut -d ' ' -f 2)
  declare -ri num_answers=$(echo $response | grep -oE 'ANSWER: \w+' | cut -d ' ' -f 2)
  declare -ri num_authorities=$(echo $response | grep -oE 'AUTHORITY: \w+' | cut -d ' ' -f 2)
  echo "  query_response: status=$status, num_answers=$num_answers, num_authorities=$num_authorities"
  if [[ $status == 'NOERROR' && $num_answers == 0 && $num_authorities -ge 1 ]]; then
    echo "  analysis: OK - Received expected response"
    return 0
  fi
  echo "  analysis: INTERFERENCE - Received unexpected response: $response"
  return 1
}

# Tests DNS interference. First tries to detect injection. If no injection,
# also tests the system resolver and verify whether the returned IPs are valid for
# the test domain.
function test_dns_blocking() {
  local domain=$1
  test_dns_injection $domain
  if [[ $? == 1 ]]; then
    # We don't test the system resolver because we know reponses are injected.
    # TODO: Consider running the system resolver test anyway, since some ISPs redirect
    # all DNS traffic to their local resolver, even if they do not block.
    return
  fi
  
  echo "SYSTEM_RESOLVER"
  declare -r resolver_ip="$(dig +short TXT whoami.ds.akahelp.net | grep ns | cut -d\" -f 4)"
  declare -r resolver_info="$(curl --silent https://ipinfo.io/${resolver_ip} |  sed 's/ *"\(.*\)": "\(.*\)",$/\1: \2/')"
  echo "  resolver_country: $(echo "$resolver_info" | grep '^country:' | cut -d' ' -f 2-)"
  echo "  resolver_ip: $(echo "$resolver_info" | grep '^ip:' | cut -d' ' -f 2-)"
  echo "  resolver_as: $(echo "$resolver_info" | grep '^org:' | cut -d' ' -f 2-)"

  declare -r ips=$(dig +dnssec +short $domain |  grep -o -E '([0-9]+\.){3}[0-9]+' | sort)
  echo "  response_ips: "$ips
  if [[ $ips == "" ]]; then
    echo "  analysis: INTERFERENCE - Did not get any IPs from the resolver"
    return 1
  fi

  # Test if IPs are valid for a given domain.
  # We first check if it's a globally addressable IP (not localhost, local network etc.)
  # Then we query Google DoH to get the IPs and use that as ground truth. If there's
  # overlap, we conclude the IPs are valid.
  # That may fail for load or geo balanced servers. In that case they will likely support
  # HTTPS. If the IP can successfuly establish a TLS connection for the domain, that's proof
  # the IP is valid for the domain.
  # The (ip, domain) validation is vulnerable to censorship (IP and SNI-based blocking), but
  # it does not have to happen at the test network. We could provide a backend for that instead.
  local ip=$(echo "$ips" | head -1)
  local ip_info=$(curl --silent "https://ipinfo.io/$ip")
  if echo "$ip_info" | grep "bogon" > /dev/null; then
    echo "  analysis: INTERFERENCE - Response IP $ip is a bogon"
    return 1
  fi

  # Validate IPs by comparing to a trusted resolution.
  # Hardcode IP address to bypass potential DNS blocking.
  # dns.google.com may still be blocked by IP or SNI. We use upper case domain to bypass some SNI blocking.
  # TODO: Check if dns.google.com is IP or SNI blocked.
  # TODO: Use ClientHello split to avoid more SNI blocking.
  # TODO: Run a DoH server for measurements on a shared IP address.
  # TODO: Recurse in case of blocking. Needs to follow CNAMES. That would still be vulnerable to blocked authoritatives.
  local ips_from_doh=$(curl --silent --connect-to ::8.8.8.8: https://DNS.GOOGLE/resolve?name=$domain |  grep -o -E '([0-9]+\.){3}[0-9]+' | sort)
  echo "  ips_from_doh: " $ips_from_doh
  local common_ips=$(comm -12 <(echo "$ips") <(echo "$ips_from_doh"))
  if (( $(echo "$common_ips" | wc -w) > 0)); then
    echo "  analysis: OK - Response IPs ["$common_ips"] were found on dns.google.com using DNS-over-HTTPS"
    return 0
  fi

  # Validate IPs by establishing a TLS connection. This is vulnerable to IP-based blocking.
  # Upper case domain may bypass SNI censorship, reducing inconclusive cases.
  local upper_domain=$(echo $domain | tr [:lower:] [:upper:])
  local curl_error
  curl_error=$(curl --silent --show-error --connect-to ::$ip: https://$upper_domain/ 2>&1 > /dev/null) 
  local result=$?
  echo "  tls_test: ip=$ip, error=$result"
  if ((result == CURLE_OK)) ; then
    echo "  analysis: OK - Response IP $ip produced certificate for domain $domain"
    return 0
  elif ((result == CURLE_PEER_FAILED_VERIFICATION)); then
    echo "  analysis: INTERFERENCE - Response $ip could not produce domain certificate"
    return 1
  elif ((result == CURLE_SSL_CACERT)); then
    echo "  analysis: INTERFERENCE - Response $ip returned a certificate with an invalid CA"
    return 1
  else
    echo "  analysis: INCONCLUSIVE - Could not validate ips ["$ips"]. TLS test failed ($curl_error)"
    return 2
  fi
  # Other tests to try:
  # - Recurse with dnssec and qname minimization
}

# The HTTP test works by connecting to a well-behaved baseline that always returns the same output
# on invalid hostname. We then compare the output for our test domain and a domain we know
# is invalid. If the result changes, then we know there was injection.
function test_http_blocking() {
  echo "HTTP"
  local domain=$1
  # TODO: use a domain we control instead of example.com, which may change without notice.
  # TODO: This breaks if the test domain is hosted in the target host.
  # TODO: This may capture censorship happening in the test server network.
  local http_response
  http_response=$(curl --silent --show-error --max-time 5 --connect-to ::example.com: http://$domain/ 2>&1)
  local http_result=$?
  if ((http_result == CURLE_OK)); then 
    local expected_reponse=$(curl --silent --show-error --max-time 5 --connect-to ::example.com: http://inexistent.example.com/ 2>&1)
    if diff <(echo "$http_response") <(echo "$expected_reponse") > /dev/null; then
      echo "  analysis: OK - Got expected response"
    else
      echo "  analysis: INTERFERENCE - Got injected response"
      diff <(echo "$http_response") <(echo "$expected_reponse")
    fi
  elif ((http_result == CURLE_GOT_NOTHING)); then
    echo "  analysis: INTERFERENCE - Unexpected empty response when Host is $domain($http_response)"
  elif ((http_result == CURLE_RECV_ERROR)); then
    echo "  analysis: INTERFERENCE - Cannot from established connection when Host is $domain($http_response)"
  elif ((http_result == CURLE_OPERATION_TIMEDOUT)); then
    echo "  analysis: LIKELY_INTERFERENCE - Unexpected time out when Host is $domain ($http_response)"
  elif ((http_result == CURLE_COULDNT_CONNECT)); then
    echo "  analysis: INCONCLUSIVE - Failed to connect to innocuous domain ($http_response)"
  else
    # TODO: Find out what errors are guaranteed blocking.
    echo "  analysis: INCONCLUSIVE - Failed to fetch test domain from innocuous domain ($http_response)"
  fi
}

# The test for SNI-triggered blocking works by connecting to a well-behaved TLS server we know
# and checking if we can get a ServerHello back when presenting the test domain. If we
# get a response without a ServerHello, which may be empty or a reset, we know it's blocked.
# If we get a ServerHello and the CA chain is valid, then we know there was no injection and
# can conclude there's no blocking.
function test_sni_blocking() {
  echo "SNI"
  local domain=$1
  # The `local` call will override `#?`, so we don't assign on the declaration.
  local curl_error
  curl_error=$(curl --silent --show-error --max-time 5 --connect-to ::example.com: "https://$domain/" 2>&1 >/dev/null)
  curl_result=$?
  if ((curl_result == CURLE_PEER_FAILED_VERIFICATION || curl_result == CURLE_OK)); then 
    echo "  analysis: OK - Got TLS ServerHello"
  elif ((curl_result == CURLE_SSL_CACERT)) && \
       [[ "$curl_error" =~ "no alternative certificate subject name matches target host name" ]]; then
    # On Linux curl outputs CURLE_SSL_CACERT for invalid subject name 🤷.
    echo "  analysis: OK - Got TLS ServerHello"
  elif ((curl_result == CURLE_GOT_NOTHING)); then
    echo "  analysis: INTERFERENCE - Unexpected empty response when SNI is $domain ($curl_error)"
  elif ((curl_result == CURLE_SSL_CONNECT_ERROR)); then
    echo "  analysis: LIKELY_INTERFERENCE - Unexpected TLS error when SNI is $domain ($curl_error)"
  else
    # TODO: Check for invalid CA chain: that indicates the server is misconfigured or
    # there's MITM going on.
    # TODO: Figure out what errors are guaranteed blocking.
    echo "  analysis: INCONCLUSIVE - Failed to get TLS ServerHello ($curl_error)"
  fi
}

function main() {
  echo time: "$(date -u)"
  if ! is_online; then
    echo "You are offline"
    return 1
  fi

  local domain=$1
  echo domain: $domain
  print_client_info
  echo

  test_dns_blocking $domain
  test_http_blocking $domain
  test_sni_blocking $domain

  # TODO: Test IP blocking
}

main $1
