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
from collections import namedtuple
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

    async def list_files(self, test_name="web_connectivity", start_date=None):
        filter_args = {"Prefix": str(self._root_path)}
        if start_date:
            filter_args["Marker"] = str(self._root_path / start_date)
        async for s3_obj in aiter(self._bucket.objects.filter(**filter_args), self._executor):
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


ReportFilenameParts = namedtuple(
    "ReportFilenameParts", ["timestamp", "country", "asn", "test_name"])


def parse_report_filename(report_filename):
    return ReportFilenameParts(*report_filename.split("-")[:4])


async def main(args):
    LOGGER.setLevel(logging.DEBUG if args.debug else logging.INFO)

    LOGGER.debug("Initializing Boto")
    # See https://ooni.torproject.org/post/mining-ooni-data/
    s3 = boto3.resource("s3")  # type: boto3.resources.base.ServiceResource
    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
    bucket = s3.Bucket("ooni-data")
    with ThreadPoolExecutor() as executor:
        ooni_client = S3OoniClient(
            bucket, "autoclaved/jsonl.tar.lz4", executor)

        file_tasks = []
        file_paths = ooni_client.list_files(
            test_name=args.test_name, start_date=args.start_date)
        if args.limit:
            file_paths = atop_n(file_paths, args.limit)
        async for file_path in file_paths:
            def file_path_to_lines(file_path, country_restrict):
                s3_file = ooni_client.fetch_file(file_path)
                if file_path.suffix == ".lz4":
                    file_path = file_path.with_name(file_path.stem)
                    s3_file = lz4.frame.open(s3_file, "r")

                with s3_file:
                    if file_path.suffix == ".json":
                        parsed_filename = parse_report_filename(file_path.name)
                        if country_restrict and parsed_filename.country != country_restrict:
                            return

                        with s3_file:
                            for line in s3_file:
                                yield line
                    elif file_path.suffix == ".tar":
                        with tarfile.open(fileobj=s3_file, mode="r|") as tar_file:
                            for entry in tar_file:
                                parsed_filename = parse_report_filename(
                                    pathlib.PurePosixPath(entry.name).name)
                                if country_restrict and parsed_filename.country != country_restrict:
                                    continue
                                for line in tar_file.extractfile(entry):
                                    yield line

            def save_measurement(measurement, domain):
                measurement_id = measurement["id"]
                country = measurement["probe_cc"]
                if not measurement_id or not domain or not country:
                    LOGGER.warning(
                        "Missing fields in measurement: %s", measurement)
                    return
                out_filename = os.path.join(
                    args.ooni_measurements, domain, country, "%s.json.gz" % measurement_id)
                os.makedirs(os.path.dirname(out_filename), exist_ok=True)
                with gzip.open(out_filename, mode="wt+") as file:
                    json.dump(measurement, file)
                LOGGER.debug("Wrote %s", out_filename)

            def process_s3_file_path(file_path, country_restrict, domain_restrict):
                for line in file_path_to_lines(file_path, country_restrict):
                    measurement = json.loads(line, encoding="utf-8")
                    domain = urlparse(measurement["input"]).hostname
                    if domain_restrict and domain != domain_restrict:
                        continue
                    save_measurement(_trim_json(measurement, 1000), domain)

            file_tasks.append(asyncio.get_event_loop().run_in_executor(
                executor, process_s3_file_path, file_path, args.country, args.domain))
        await asyncio.gather(*file_tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "List OONI files")
    parser.add_argument("--ooni_measurements", type=str, required=True)
    parser.add_argument("--test_name", type=str, default="web_connectivity")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--start_date", type=str)
    parser.add_argument("--country", type=str)
    # Domain restriction is slow!
    parser.add_argument("--domain", type=str)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.get_event_loop().run_until_complete(
        main(args)))
