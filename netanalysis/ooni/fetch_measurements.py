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

# pylint: disable=yield-inside-async-function

import argparse
import asyncio
from concurrent.futures import Executor, ThreadPoolExecutor
import ipaddress
import logging
import os
import ssl
import sys
from urllib.parse import urlparse

import aiohttp
import certifi
import iso3166
import ujson as json

import netanalysis.ooni.ooni_client as oc

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

async def aenumerate(inner):
    index = 0
    async for item in inner:
        yield index, item
        index += 1


async def atop_n(inner, n: int):
    remaining = n
    async for item in inner:
        if remaining <= 0:
            return
        yield item
        remaining -= 1


def main(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    executor = ThreadPoolExecutor()
    tcp_connector = aiohttp.TCPConnector(
        limit_per_host=args.ooni_connections, ssl_context=_SSL_CONTEXT)
    query_country = args.country.upper()
    if query_country == "*": query_country = None
    query_url = args.url
    if query_url == "*": query_url = None

    async def fetch_measurements():
        async with aiohttp.ClientSession(connector=tcp_connector) as http_client:
            ooni_client = oc.CreatePublicApiOoniClient(http_client)

            country_list = [query_country]
            if query_country == "ALL":
                # Fetching ALL takes around 5h 30m!!!
                country_list = sorted([c.alpha2 for c in iso3166.countries])
            for country_code in country_list:
                if country_code:
                    logging.info("Processing country %s (%s)", country_code,
                                iso3166.countries.get(country_code).name)
                measurement_futures = []
                async for index, entry in aenumerate(atop_n(
                    ooni_client.list_measurements(country_code, query_url),
                                                args.num_measurements)):
                    if index % 10 == 9:
                        logging.info("Measurement %d of %d", index + 1, args.num_measurements)
                    measurement_id = entry["measurement_id"]
                    domain = urlparse(entry["input"]).hostname
                    country = entry["probe_cc"].upper()
                    if not domain:
                        logging.warning("Domain missing for url %s in measurement %s",
                                        entry["input"], measurement_id)
                        continue
                    if not country:
                        logging.warning("Country missing in measurement %s", measurement_id)
                        continue
                    filename = os.path.join(
                        args.output_dir, domain, country, "%s.json" % measurement_id)
                    try:
                        if os.stat(filename).st_size > 0:
                            logging.debug("Skipping %s", filename)
                            continue
                    except FileNotFoundError:
                        pass

                    async def get_and_save_measurement(measurement_id, filename):
                        logging.debug("Fetching %s", filename)
                        measurement = await ooni_client.get_measurement(measurement_id)

                        def write_file(measurement, filename):
                            logging.debug("Writing %s", filename)
                            os.makedirs(os.path.dirname(filename), exist_ok=True)
                            with open(filename, mode="w+") as out_file:
                                json.dump(measurement, out_file)
                        await asyncio.get_event_loop().run_in_executor(executor, write_file, measurement, filename)
                    logging.debug("Queueing %s", filename)
                    measurement_futures.append(asyncio.ensure_future(
                        get_and_save_measurement(measurement_id, filename)))
                if measurement_futures:
                    await asyncio.wait(measurement_futures)

    asyncio.get_event_loop().run_until_complete(fetch_measurements())


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Fetch OONI measurements")
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--country", type=str, required=True)
    parser.add_argument("--url", type=str, required=True)
    parser.add_argument("--num_measurements", type=int, default=100)
    parser.add_argument("--ooni_connections", type=int, default=10)
    parser.add_argument("--debug", action="store_true")
    sys.exit(main(parser.parse_args()))
