#!/usr/bin/python
#
# Copyright 2020 Jigsaw Operations LLC
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
from contextlib import closing
import datetime as dt
from functools import singledispatch
import gzip
import io
import logging
from multiprocessing.pool import ThreadPool
import os
from os import PathLike
import pathlib
from pathlib import PosixPath
import posixpath
import sys
from tempfile import TemporaryDirectory
from typing import IO, Iterable, List, Tuple

import boto3
from botocore import UNSIGNED
from botocore.config import Config
import lz4.frame
import ujson


def filename_matches(filename: str, measurement_type: str, country: str) -> bool:
    basename = posixpath.basename(filename)
    parts = basename.split('-')
    if len(parts) < 4:
        return False
    return parts[1] == country and parts[3] == measurement_type


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


def list_files_with_index(date: str, measurement_type: str, country: str):
    client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    stream = client.get_object(Bucket='ooni-data', Key=f'autoclaved/jsonl.tar.lz4/{date}/index.json.gz')['Body']
    files = []
    with gzip.open(stream, mode='rt', encoding='utf8') as json_lines:
        current_file = {}
        current_frame = {}
        output = False
        for line in json_lines:
            entry = ujson.loads(line)
            if entry['type'] == 'file':
                current_file = entry
                current_file['frames'] = []
            elif entry['type'] == '/file':
                if len(current_file.get('frames', [])) > 0:
                    files.append(current_file)
                    current_file = {}
            elif entry['type'] == 'report':
                report_name = entry['textname']
                if filename_matches(report_name, measurement_type, country):
                    output = True
            elif entry['type'] == '/report':
                output = False
            elif entry['type'] == 'frame':
                current_frame = entry
                current_frame['data'] = []
            elif entry['type'] == '/frame':
                if len(current_frame.get('data', [])) > 0:
                    current_file['frames'].append(current_frame)
                    current_frame = {}
            elif entry['type'] == 'datum':
                if output:
                    current_frame['data'].append(entry)

    # TODO:
    # - Process segment by segment
    # - Parallelize large files
    # - Trim JSON
    # - Checkpoints
    total_size = 0
    total_measurements = 0
    total_frames = 0
    for file in files:
        print(f'File {file["filename"]}')
        frames = file['frames']
        fi = 0
        while fi < len(frames):
            next_frame_pos = frames[fi]['file_off']
            segment = []
            while fi < len(frames) and frames[fi]['file_off'] == next_frame_pos:
                next_frame_pos += frames[fi]['file_size']
                segment.append(frames[fi])
                total_frames += 1
                total_measurements += len(frames[fi]['data'])
                total_size += frames[fi]['file_size']
                fi += 1
            segment_start = segment[0]['file_off']
            segment_end = segment[-1]['file_off'] + segment[-1]['file_size']
            segment_bytes = segment_end - segment_start
            print(f'  Segment frames: {len(segment):,}, bytes: {segment_bytes:,}')
            s3_key = f'autoclaved/jsonl.tar.lz4/{file["filename"]}'
            stream = client.get_object(Bucket='ooni-data', Key=s3_key, Range=f'{segment_start}-{segment_end - 1}')['Body']
            with lz4.frame.LZ4FrameFile(stream, mode='r') as lz4_file:
                bytes_read = 0
                for frame in segment:
                    for entry in frame['data']:
                        skip = entry['text_off'] - bytes_read
                        if skip > 0:
                            lz4_file.read(skip)
                        measurement = ujson.loads(lz4_file.read(size=entry['text_size']))
                        measurement = trim_measurement(measurement, 1000)
                        bytes_read = entry['text_off'] + entry['text_size']
                        # pprint(measurement)
                        print(dict(
                            country=measurement.get('probe_cc'),
                            input=measurement.get('input'),
                            asn=f'{measurement.get("probe_asn")} ({measurement.get("probe_network_name")})',
                            url=f'https://explorer.ooni.org/measurement/{measurement.get("report_id")}?input={measurement.get("input")}',
                        ))

    print(f'Frames: {total_frames:,}, Measurements: {total_measurements:,}, Size: {total_size:,}')
    # From https://aws.amazon.com/s3/pricing/
    data_cost = 0.09 * total_size / 2**30  # $0.09 per GiB
    request_cost = 0.0004 * total_frames / 1000
    print(f'Requests: ${request_cost:0.6f}, Data: ${data_cost:0.6f},  Total: ${data_cost + request_cost:0.6f}')
    print(f'Download time: {total_size / 85000000 * 8:.2f}s @ 85 Mbps, {total_size / 10000000 * 8:.2f}s @ 10 Mbps')


class FileEntry:
    def __init__(self, bucket: 'Bucket', test_type: str, country: str, date: dt.date, file_path: PosixPath, size: int) -> None:
        self._bucket = bucket
        self.test_type = test_type
        self.country = country
        self.date = date
        self.file_path = file_path
        self.size = size

    def get_file(self) -> IO:
        return self._bucket.get_file(self.file_path)


class Bucket:
    def __init__(self, bucket='ooni-data-eu-fra', prefix='raw/'):
        self._client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
        self._bucket = bucket
        self._prefix = prefix

    def list_files(self, first_date: dt.date, last_date: dt.date, test_type: str, country: str) -> Iterable[FileEntry]:
        paginator = self._client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=self._bucket,
            Delimiter='/',
            Prefix=self._prefix,
            StartAfter=f'{self._prefix}{first_date.strftime("%Y%m%d")}',
        )
        for page in pages:
            for date_entry in page.get('CommonPrefixes', []):
                date_str = posixpath.basename(posixpath.dirname(date_entry['Prefix']))
                date = dt.datetime.strptime(date_str, "%Y%m%d").date()
                if date > last_date:
                    return
                for hour in range(24):
                    prefix = f'''{date_entry['Prefix']}{hour:02}/{country}/'''
                    if test_type:
                        prefix += f'{test_type}/'
                    for page in paginator.paginate(Bucket=page['Name'], Prefix=prefix):
                        for entry in page.get('Contents', []):
                            key = entry['Key']
                            # Remove prefix
                            file_path = pathlib.PosixPath(key[len(self._prefix):])
                            if file_path.name.endswith('.jsonl.gz'):
                                file_test_type = file_path.parent.name
                                yield FileEntry(self, file_test_type, country, date, file_path, entry['Size'])

    def get_file(self, filename: PosixPath):
        key = f'{self._prefix}{filename}'
        return self._client.get_object(Bucket=self._bucket, Key=key)['Body']


class LocalMeasurements:
    def __init__(self, data_dir: PathLike) -> None:
        self._data_dir = pathlib.Path(data_dir)

    def _make_path(self, country: str, test_type: str, date: dt.datetime, basename: str) -> pathlib.Path:
        return self._data_dir / country / test_type / f'{date:%Y%m%d}' / basename

    def has(self, country: str, test_type: str, date: dt.datetime, basename: str):
        return self._make_path(country, test_type, date, basename).is_file()

    def save(self, country: str, test_type: str, date: dt.datetime, basename: str, measurements_file: IO):
        with TemporaryDirectory() as temp_dir:
            temp_filename = pathlib.Path(temp_dir) / basename
            with gzip.open(temp_filename, mode='wt', encoding='utf-8', newline='\n') as local_file:
                for line in measurements_file:
                    measurement = ujson.loads(line)
                    ujson.dump(trim_measurement(measurement,  1000), local_file)
                    local_file.write('\n')
            file_path = self._make_path(country, test_type, date, basename)
            os.makedirs(file_path.parent, exist_ok=True)
            temp_filename.rename(file_path)

    def get_measurements(self, country: str, test_type: str):
        for root, _, files in os.walk(self._data_dir / country / test_type):
            for filename in files:
                with gzip.open(os.path.join(root, filename), 'r') as test_file:
                    for line in test_file:
                        yield ujson.loads(line)


class CostLimitError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def sync_measurements(local_measurements: LocalMeasurements, entries: Iterable[FileEntry], cost_usd_limit=1.00) -> Tuple[int, int]:
    COST_USD_PER_GIB = 0.09
    data_limit_bytes = cost_usd_limit / COST_USD_PER_GIB * 2**30
    downloaded_bytes = 0

    def sync_entry(entry: FileEntry):
        nonlocal downloaded_bytes
        if local_measurements.has(entry.country, entry.test_type, entry.date, entry.file_path.name):
            return f'Skipping {entry.file_path} [{entry.size:,} bytes]'
        if downloaded_bytes + entry.size > data_limit_bytes:
            raise CostLimitError(f'Downloaded {downloaded_bytes / 2**30} GiB')
        downloaded_bytes += entry.size
        with closing(entry.get_file()) as remote_file, gzip.GzipFile(fileobj=remote_file, mode='r') as uncompressed_file:
            local_measurements.save(entry.country, entry.test_type, entry.date, entry.file_path.name, uncompressed_file)
        return f'Downloaded {entry.file_path} [{entry.size:,} bytes]'

    with ThreadPool(processes = 5 * os.cpu_count()) as sync_pool:
        for msg in sync_pool.imap_unordered(sync_entry, entries):
            print(msg, flush=True)

    download_cost = downloaded_bytes * COST_USD_PER_GIB / 2**30
    return downloaded_bytes, download_cost


def get_measurements(file):
    with io.TextIOWrapper(gzip.GzipFile(fileobj=file, mode='r'), encoding='utf-8') as json_lines:
        for line in json_lines:
            yield trim_measurement(ujson.loads(line), 1000)


def main(args):
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    ooni = Bucket()
    # list_files_with_index(args.date, 'web_connectivity', args.country)
    for filename in ooni.list_files(dt.date(2020, 10, 26), dt.date(2020, 11, 2), None, args.country):
        print(filename)
        # with ooni.get_file(filename) as file:
        #     for measurement in itertools.islice(get_measurements(file), 1):
        #         print(measurement)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "List OONI measurements")
    # parser.add_argument("--ooni_measurements_dir", type=str, required=True)
    # parser.add_argument("--dns_measurements", type=str)
    parser.add_argument("--country", type=str, required=True)
    parser.add_argument("--date", type=str, required=True)
    parser.add_argument("--debug", action="store_true")
    sys.exit(main(parser.parse_args()))
