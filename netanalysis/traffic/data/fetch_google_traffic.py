#!/usr/bin/python
#
# Copyright 2019 Jigsaw Operations LLC
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
Get the traffic data from the Google Transparency Report and save as CSV.

It will save a file for each region as ${OUTPUT_DIR}/[REGION_CODE]/[PRODUCT_NAME]:[PRODUCT_CODE].csv
"""
import argparse
import csv
import datetime
import logging
import os
import sys

from netanalysis.traffic.data import model
import netanalysis.traffic.data.api_repository as api

logging.getLogger().setLevel(logging.INFO)

def main(args):
    if not args.output_dir:
        logging.error("Need to specify output directory")
        return 1
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    report = api.ApiTrafficRepository()  # type: modelTrafficRepository
    if args.products:
        product_id_list = [model.ProductId[ps.strip().upper()] for ps in args.products.split(",")]
    else:
        product_id_list = [p for p in model.ProductId if p.value != model.ProductId.UNKNOWN]
    region_code_list = report.list_regions()
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(days=5*365)
    for region_code in region_code_list:
        logging.info("Processing region %s", region_code)
        output_region_directory = os.path.join(args.output_dir, region_code)
        if not os.path.exists(output_region_directory):
            os.makedirs(output_region_directory)

        for product_id in product_id_list:
            logging.info("Fetching traffic data for region %s product %s", region_code, product_id.name)
            csv_filename = os.path.join(output_region_directory, "%s.csv" % product_id.name)
            if os.path.exists(csv_filename):
                logging.info("Traffic data already available for %s in %s. Skipping...",
                    product_id.name, region_code)
                continue
            try:
                traffic_series = report.get_traffic(region_code, product_id, start_time, end_time)
                if traffic_series.empty:
                    logging.info("No traffic for product %s in region %s", product_id.name, region_code)
                    continue
                with open(csv_filename, "w") as csv_file:
                    writer = csv.writer(csv_file)
                    for entry in traffic_series.iteritems():
                        writer.writerow((entry[0].isoformat(), entry[1]))
            except Exception as error:
                logging.warning("Failed to get traffic for %s %s: %s", \
                    region_code, product_id.name, str(error))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Fetches traffic data from the Google Transparency Report as CSV')
    parser.add_argument("--output_dir", type=str, required=True, help='The base directory for the output')
    parser.add_argument("--products", type=str,
        help="Comma-separated list of the products to get traffic for")
    sys.exit(main(parser.parse_args()))
