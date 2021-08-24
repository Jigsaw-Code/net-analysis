# Website Blocking Test

To test if and how a domain `$DOMAIN` is blocked, run:
```
./measure.sh $DOMAIN
```

Here is an example output for SNI-based blocking of Signal in Uzbekistan:
```
$ bash measure.sh www.signal.org
time: Sat Jul  3 18:05:15 UTC 2021
domain: www.signal.org
client_country: UZ
client_as: AS8193 Uzbektelekom Joint Stock Company

DNS_INJECTION
  root_nameserver: l.root-servers.net.
  query_response: status=NOERROR, num_answers=0, num_authorities=6
  analysis: OK - Received expected response
SYSTEM_RESOLVER
  resolver_country: UZ
  resolver_ip: 185.74.5.210
  resolver_as: AS202660 Uzbektelekom Joint Stock Company
  response_ips: 13.32.123.28 13.32.123.33 13.32.123.43 13.32.123.56
  ips_from_doh:  13.32.123.28 13.32.123.33 13.32.123.43 13.32.123.56
  analysis: OK - Response IPs [13.32.123.28 13.32.123.33 13.32.123.43 13.32.123.56] were found on dns.google.com using DNS-over-HTTPS
HTTP
  analysis: OK - Got expected response
SNI
  analysis: INCONCLUSIVE - Failed to get TLS ServerHello (curl: (28) Operation timed out after 5001 milliseconds with 0 out of 0 bytes received)
```


For more examples of this script being used in practice, see the [discussion on blocking in Uzbekistan in July 2021](https://ntc.party/t/twitter-tik-tok-skype/1122/15).
