#!/usr/bin/python
#
# Copyright 2021 Jigsaw Operations LLC
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

import argparse
import datetime as dt
from functools import singledispatch
import gzip
import logging
from multiprocessing.pool import ThreadPool
import os
import pathlib
import sys
from typing import List

import ujson

from . import ooni_client


@singledispatch
def trim_measurement(json_obj, max_string_size: int):
    return json_obj


@trim_measurement.register(dict)
def _(json_dict: dict, max_string_size: int):
    keys_to_delete: List[str] = []
    for key, value in json_dict.items():
        if type(value) == str and len(value) > max_string_size:
            keys_to_delete.append(key)
        else:
            trim_measurement(value, max_string_size)
    for key in keys_to_delete:
        del json_dict[key]
    return json_dict


@trim_measurement.register(list)
def _(json_list: list, max_string_size: int):
    for item in json_list:
        trim_measurement(item, max_string_size)
    return json_list


class CostLimitError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def main(args):
    logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    ooni = ooni_client.OoniClient()
    file_entries = ooni.list_files(
        args.first_date, args.last_date, args.test_type, args.country)

    def fetch_file(entry: ooni_client.FileEntry):
        basename = pathlib.PurePosixPath(entry.url.path).name
        # Fix .json.lz4 and .tar.lz4 filenames.
        if not basename.endswith('.jsonl.gz'):
            basename = basename.rsplit('.', 2)[0] + '.jsonl.gz'

        target_filename = args.output_dir / entry.country / \
            f'{entry.date:%Y-%m-%d}' / basename
        os.makedirs(target_filename.parent, exist_ok=True)
        if ooni.cost_usd > args.cost_limit_usd:
            raise CostLimitError(
                f'Downloaded {ooni.bytes_downloaded / 2**20} MiB')
        with gzip.open(target_filename, mode='wt', encoding='utf-8', newline='\n') as target_file:
            for measurement in entry.get_measurements():
                m = trim_measurement(measurement, args.max_string_size)
                ujson.dump(m, target_file)
                target_file.write('\n')
        return f'Downloaded {entry.url.geturl()} [{entry.size:,} bytes]'

    with ThreadPool(processes=5 * os.cpu_count()) as sync_pool:
        for msg in sync_pool.imap_unordered(fetch_file, file_entries):
            logging.info(msg)

    logging.info(f'Download size: {ooni.bytes_downloaded/2**20:0.3f} MiB, Estimated Cost: ${ooni.cost_usd:02f}')


def _parse_date_flag(date_str: str) -> dt.date:
    return dt.datetime.strptime(date_str, "%Y-%m-%d").date()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Fetch OONI measurements")
    parser.add_argument("--country", type=str, required=True)
    parser.add_argument("--first_date", type=_parse_date_flag,
                        default=dt.date.today() - dt.timedelta(days=14))
    parser.add_argument("--last_date", type=_parse_date_flag,
                        default=dt.date.today())
    parser.add_argument("--test_type", type=str, default='webconnectivity')
    parser.add_argument("--max_string_size", type=int, default=1000)
    parser.add_argument("--cost_limit_usd", type=float, default=1.00)
    parser.add_argument("--output_dir", type=pathlib.Path, required=True)
    parser.add_argument("--debug", action="store_true")
    sys.exit(main(parser.parse_args()))
