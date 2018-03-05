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

import argparse
import asyncio
from concurrent.futures import Executor, ThreadPoolExecutor
from functools import singledispatch
import gzip
import itertools
import json
import logging
import os.path
import pathlib
import sys
import tarfile
from typing import Iterable, TextIO, Tuple
from urllib.parse import urlparse

import boto3
from botocore.handlers import disable_signing
import botocore.response
import lz4.frame

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(name="list_ooni_files")  # type: logging.Logger


async def atop_n(inner, n: int):
    remaining = n
    async for item in inner:
        if remaining <= 0:
            return
        yield item
        remaining -= 1


async def aiter(iterable, executor):
    iterator = iter(iterable)
    while True:
        value = await asyncio.get_event_loop().run_in_executor(executor, next, iterator, None)
        if value is None:
            return
        yield value


class S3OoniClient:
    def __init__(self, bucket, root_path: str, executor: Executor):
        self._bucket = bucket
        self._root_path = pathlib.PurePosixPath(root_path)
        self._executor = executor

    async def list_files(self, test_name="web_connectivity", prefix=""):
        async for s3_obj in aiter(self._bucket.objects.filter(Prefix=str(self._root_path / prefix)),
                                  self._executor):
            report_path = pathlib.PurePosixPath(
                s3_obj.key).relative_to(self._root_path)
            if test_name and (test_name not in report_path.name):
                continue
            yield report_path

    def fetch_file(self, filename):
        key = str(self._root_path.joinpath(filename))
        s3_obj = self._bucket.Object(key)
        return s3_obj.get()["Body"]


@singledispatch
def _trim_json(json_obj, max_string_size: int):
    return json_obj


@_trim_json.register(dict)
def _(json_dict: dict, max_string_size: int):
    keys_to_delete = []  # type: str
    for key, value in json_dict.items():
        if type(value) == str and len(value) > max_string_size:
            keys_to_delete.append(key)
        else:
            _trim_json(value, max_string_size)
    for key in keys_to_delete:
        del json_dict[key]
    return json_dict


@_trim_json.register(list)
def _(json_list: list, max_string_size: int):
    for item in json_list:
        _trim_json(item, max_string_size)
    return json_list


async def main(args):
    LOGGER.setLevel(logging.DEBUG if args.debug else logging.INFO)

    LOGGER.debug("Initializing Boto")
    # See https://ooni.torproject.org/post/mining-ooni-data/
    s3 = boto3.resource("s3")  # type: boto3.resources.base.ServiceResource
    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
    bucket = s3.Bucket("ooni-data")
    with ThreadPoolExecutor(10) as executor:
        ooni_client = S3OoniClient(
            bucket, "autoclaved/jsonl.tar.lz4", executor)

        file_tasks = []
        async for file_path in atop_n(
                ooni_client.list_files(test_name=args.test_name, prefix=args.prefix), args.limit):
            def process_report_file(file_obj):
                count = 0
                for line in file_obj:
                    measurement_json = _trim_json(
                        json.loads(line, encoding="utf-8"), 1000)
                    measurement_id = measurement_json["id"]
                    domain = urlparse(measurement_json["input"]).hostname
                    country = measurement_json["probe_cc"]
                    out_filename = os.path.join(
                        args.ooni_measurements, domain, country, "%s.json.gz" % measurement_id)
                    os.makedirs(os.path.dirname(out_filename), exist_ok=True)
                    with gzip.open(out_filename, mode="wt+") as file:
                        json.dump(measurement_json, file)
                    LOGGER.debug("Wrote %s", out_filename)
                    count += 1

            def process_s3_file(file_path):
                try:
                    report_file = ooni_client.fetch_file(file_path)
                    if file_path.suffix == ".lz4":
                        file_path = file_path.with_name(file_path.stem)
                        report_file = lz4.frame.open(report_file, "r")
                    if file_path.suffix == ".tar":
                        with tarfile.open(fileobj=report_file, mode="r|") as tar_file:
                            for entry in tar_file:
                                print("Filename (tar): %s" % entry.name)
                                process_report_file(
                                    tar_file.extractfile(entry))
                    else:
                        print("Filename: %s" % file_path)
                        process_report_file(report_file)
                finally:
                    if report_file:
                        report_file.close()
            file_tasks.append(asyncio.get_event_loop().run_in_executor(
                executor, process_s3_file, file_path))
        await asyncio.gather(*file_tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "List OONI files")
    parser.add_argument("--ooni_measurements", type=str, required=True)
    parser.add_argument("--test_name", type=str, default="web_connectivity")
    parser.add_argument("--prefix", type=str, default="")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--debug", action="store_true")
    sys.exit(asyncio.get_event_loop().run_until_complete(
        main(parser.parse_args())))
