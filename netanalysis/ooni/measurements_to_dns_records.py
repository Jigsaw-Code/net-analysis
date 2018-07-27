#!/usr/bin/python
#
# Copyright 2018 Jigsaw Operations LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Reads OONI measurements and outputs the DNS resource records.

Sample usage:
  .venv/bin/python -m netanalysis.ooni.measurements_to_dns_records \
      --ooni_measurements_dir=ooni_data/
"""

import argparse
import asyncio
import datetime
import glob
import ipaddress
import itertools
import logging
import os
import os.path
import pprint
import sys
from typing import Iterable, List
from urllib.parse import urlparse

import ujson as json

from netanalysis.dns import model as dns
from netanalysis.dns import serialization as ds


def parse_ooni_date(date_str: str) -> datetime.datetime:
    # TODO: Set the timezone
    return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


def get_control_dns_measurement(measurement, measurement_id):
    measurement_time = parse_ooni_date(
        measurement.get("measurement_start_time")).isoformat()

    try:
        addresses = measurement["test_keys"]["control"]["dns"]["addrs"]
    except KeyError:
        raise ValueError("OONI Control Measurement without test_keys.control.dns.addrs: %s" %
                         pprint.pformat(measurement, compact=True))
    if not addresses:
        raise ValueError("OONI Control Measurement with empty test_keys.control.dns.addrs: %s" %
                         pprint.pformat(measurement, compact=True))
    records = []  # type: List[dns.ResourceRecord]
    last_cname = urlparse(measurement.get("input")).hostname
    for address in addresses:
        try:
            records.append(dns.ResourceRecord(
                last_cname, dns.IpAddressData(address)))
        except ValueError:
            records.append(dns.ResourceRecord(
                last_cname, dns.CnameData(address)))
        last_cname = address

    measurement_time = parse_ooni_date(
        measurement.get("measurement_start_time")).isoformat()
    return dns.DnsMeasurement(
        measurement_id="%s:control" % measurement_id,
        records=records,
        time=measurement_time,
        provenance="ooni:%s" % measurement_id,
        trust_reason="IN_OONI_CONTROL"
    )


def get_experiment_dns_measurement(measurement, measurement_id) -> dns.DnsMeasurement:
    measurement_time = parse_ooni_date(
        measurement.get("measurement_start_time")).isoformat()
    try:
        ooni_queries = measurement["test_keys"]["queries"]
    except KeyError:
        raise ValueError("OONI Measurement without test_keys.queries: %s" %
                         pprint.pformat(measurement, compact=True))
    if not ooni_queries:
        raise ValueError("OONI Measurement with empty test_keys.queries: %s" %
                         pprint.pformat(measurement, compact=True))
    records = []  # type: List[dns.ResourceRecord]
    for ooni_query in ooni_queries:
        last_cname = ooni_query.get("hostname")
        if not last_cname:
            logging.warning("Missing hostname in query %s", ooni_query)
        for ooni_answer in ooni_query.get("answers"):
            cname = ooni_answer.get("hostname")
            if cname:
                if cname == last_cname:
                    continue
                records.append(dns.ResourceRecord(
                    last_cname, dns.CnameData(cname)))
                last_cname = cname
            else:
                ip_str = ooni_answer.get("ipv4") or ooni_answer.get("ipv6")
                if ip_str:
                    try:
                        records.append(dns.ResourceRecord(
                            last_cname, dns.IpAddressData(ip_str)))
                    except ValueError:
                        logging.warning(
                            "Measurement %s: invalid IP answer %s", measurement["id"], ip_str)
    measurement_time = parse_ooni_date(
        measurement.get("measurement_start_time")).isoformat()
    resolver_ip_str = measurement["test_keys"].get("client_resolver")
    resolver_ip = ipaddress.ip_address(
        resolver_ip_str) if resolver_ip_str else None
    return dns.DnsMeasurement(
        measurement_id=measurement_id,
        records=records,
        time=measurement_time,
        resolver_ip=resolver_ip,
        client_asn=int(measurement.get("probe_asn")[2:]),
        client_country=measurement.get("probe_cc"),
        provenance="ooni:%s" % measurement_id,
    )


def read_ooni_dns_measurements(ooni_measurements_dir: str) -> Iterable[dns.DnsMeasurement]:
    for domain_country_dir in sorted(glob.iglob(os.path.join(ooni_measurements_dir, "*", "*"))):
        for filename in glob.iglob(os.path.join(domain_country_dir, "*")):
            with open(filename) as file:
                measurement = json.load(file)
                measurement_id = os.path.splitext(
                    os.path.basename(filename))[0]
                try:
                    yield get_control_dns_measurement(measurement, measurement_id)
                except ValueError as e:
                    logging.debug(e)
                try:
                    yield get_experiment_dns_measurement(measurement, measurement_id)
                except ValueError as e:
                    logging.debug(e)
        logging.info("Done with %s", domain_country_dir)


def main(args):
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    if not args.dns_measurements:
        args.dns_measurements = os.path.join(
            args.ooni_measurements_dir, "dns_records.json")

    os.makedirs(os.path.dirname(args.dns_measurements), exist_ok=True)
    with open(args.dns_measurements, "w") as dns_measurements:
        for measurement in read_ooni_dns_measurements(args.ooni_measurements_dir):
            dns_measurements.write(json.dumps(ds.to_json(measurement)))
            dns_measurements.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Convert OONI measurements to DNS Resolutions")
    parser.add_argument("--ooni_measurements_dir", type=str, required=True)
    parser.add_argument("--dns_measurements", type=str)
    parser.add_argument("--debug", action="store_true")
    sys.exit(main(parser.parse_args()))
