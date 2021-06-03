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

import datetime as dt
from contextlib import closing
import gzip
from pathlib import PosixPath
import posixpath
from typing import Callable, Dict, Iterable
from urllib.parse import SplitResult

import boto3
from botocore import UNSIGNED
from botocore.config import Config
import lz4.frame
import ujson


class FileEntry:
    """Represents a file entry in the OONI S3 Bucket."""

    def __init__(self, get_measurements: Callable[[], Iterable[object]], test_type: str, country: str, date: dt.date, url: SplitResult, size: int) -> None:
        self.get_measurements = get_measurements
        self.test_type = test_type
        self.country = country
        self.date = date
        self.url = url
        self.size = size


class OoniClient:
    def __init__(self):
        s3_client = boto3.client(
            's3', config=Config(signature_version=UNSIGNED))
        self._new_client = _2020OoniClient(s3_client)
        self._legacy_client = _LegacyOoniClient(s3_client)

    @property
    def num_list_requests(self) -> int:
        return self._new_client.num_list_requests + self._legacy_client.num_list_requests

    @property
    def num_get_requests(self) -> int:
        return self._new_client.num_get_requests + self._legacy_client.num_get_requests

    @property
    def bytes_downloaded(self) -> int:
        return self._new_client.bytes_downloaded + self._legacy_client.bytes_downloaded

    @property
    def cost_usd(self) -> float:
        # From https://aws.amazon.com/s3/pricing/
        data_cost = 0.09 * self.bytes_downloaded / 2**30  # $0.09 per GiB
        request_cost = (0.0004 * self.num_get_requests / 1000 +
                        0.005 * self.num_list_requests / 1000)
        return data_cost + request_cost

    def list_files(self, first_date: dt.date, last_date: dt.date, test_type: str, country: str) -> Iterable[FileEntry]:
        yield from self._legacy_client.list_files(first_date, last_date, test_type, country)
        yield from self._new_client.list_files(first_date, last_date, test_type, country)


class _2020OoniClient:
    _BUCKET = 'ooni-data-eu-fra'
    _PREFIX = 'raw/'

    def __init__(self, s3_client):
        self._s3_client = s3_client
        self.num_get_requests = 0
        self.num_list_requests = 0
        self.bytes_downloaded = 0

    # Example files: `aws --no-sign-request s3 ls s3://ooni-data-eu-fra/raw/20210526/00/VE/webconnectivity/`
    # First directory in the new bucket is 20201020/
    def list_files(self, first_date: dt.date, last_date: dt.date, test_type: str, country: str) -> Iterable[FileEntry]:
        if last_date < dt.date(2020, 10, 20):
            return
        paginator = self._s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=_2020OoniClient._BUCKET, Delimiter='/', Prefix=_2020OoniClient._PREFIX,
                                   StartAfter=f'{_2020OoniClient._PREFIX}{first_date.strftime("%Y%m%d")}')
        for page in pages:
            self.num_list_requests += 1
            for entry in page.get('CommonPrefixes', []):
                date_dir = entry['Prefix']
                date_str = posixpath.basename(posixpath.dirname(date_dir))
                date = dt.datetime.strptime(date_str, "%Y%m%d").date()
                if date > last_date:
                    return
                for hour in range(24):
                    prefix = f'''{date_dir}{hour:02}/{country}/'''
                    if test_type:
                        prefix += f'{test_type}/'
                    for page in paginator.paginate(Bucket=page['Name'], Prefix=prefix):
                        self.num_list_requests += 1
                        for entry in page.get('Contents', []):
                            key = entry['Key']
                            file_path = PosixPath(key)
                            if file_path.name.endswith('.jsonl.gz'):
                                file_test_type = file_path.parent.name
                                url = SplitResult(
                                    's3', page['Name'], key, None, None)
                                yield FileEntry(lambda: self._get_measurements(url), file_test_type, country, date, url, entry['Size'])

    def _get_measurements(self, url: SplitResult) -> Iterable[Dict]:
        s3_object = self._s3_client.get_object(Bucket=url.netloc, Key=url.path)
        self.num_get_requests += 1
        self.bytes_downloaded += s3_object['ContentLength']
        with closing(s3_object['Body']) as remote_file, gzip.GzipFile(fileobj=remote_file, mode='r') as source_file:
            for line in source_file:
                yield ujson.loads(line)


class _LegacyOoniClient:
    _BUCKET = 'ooni-data'
    _PREFIX = 'autoclaved/jsonl.tar.lz4/'

    @staticmethod
    def _test_type_for_match(measurement_type: str):
        return measurement_type.replace('_', '')

    # Example filename: 20200801T144129Z-BR-AS28573-web_connectivity-20200801T144133Z_AS28573_hlwQt15JxAkU6kYEfTrZL8JbTrTY06WzBRAUIu6zR4b6H3ww7m-0.2.0-probe.json.lz4
    @staticmethod
    def _filename_matches(filename: str, test_type: str, country: str) -> bool:
        basename = posixpath.basename(filename)
        parts = basename.split('-')
        if len(parts) < 4:
            return False
        return parts[1] == country and _LegacyOoniClient._test_type_for_match(parts[3]) == test_type

    @staticmethod
    def _files_from_index(json_lines: Iterable[str], test_type: str, country: str):
        # Format defined at https://ooni.org/post/mining-ooni-data/
        # file is a lz4 file on S3. Key "filename" is the file name.
        # report is a standalone json.lz4 file, or a file embedded in a tar.lz4 file set. Keys "textname" is the jsonl report name.
        # datum is a single measurement as a JSON object.
        # frame is a LZ4 frame with multiple measurements. Its boundaries don't necessarily align with files or reports.
        current_file = {}
        current_frame = {}
        output_measurements = False
        for line in json_lines:
            entry = ujson.loads(line)
            if entry['type'] == 'file':
                current_file = entry
                current_file['frames'] = []
            elif entry['type'] == '/file':
                if len(current_file.get('frames', [])) > 0:
                    yield current_file
                current_file = {}
            elif entry['type'] == 'report':
                report_name = entry['textname']
                if _LegacyOoniClient._filename_matches(report_name, test_type, country):
                    output_measurements = True
            elif entry['type'] == '/report':
                output_measurements = False
            elif entry['type'] == 'frame':
                current_frame = entry
                current_frame['data'] = []
            elif entry['type'] == '/frame':
                if len(current_frame.get('data', [])) > 0:
                    current_file['frames'].append(current_frame)
                    current_frame = {}
            elif entry['type'] == 'datum':
                if output_measurements:
                    current_frame['data'].append(entry)

    @staticmethod
    def _frame_bytes(frames: Iterable[Dict]) -> int:
        bytes = 0
        for frame in frames:
            bytes += frame['file_size']
        return bytes

    def __init__(self, s3_client):
        self._s3_client = s3_client
        self.num_get_requests = 0
        self.num_list_requests = 0
        self.bytes_downloaded = 0

    # Example files: `aws --no-sign-request s3 ls s3://ooni-data/autoclaved/jsonl.tar.lz4/2020-08-01/`
    # First directory is 2012-12-05/, last is 2020-10-21/.
    def list_files(self, first_date: dt.date, last_date: dt.date, test_type: str, country: str) -> Iterable[FileEntry]:
        if first_date > dt.date(2020, 10, 21):
            return
        paginator = self._s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=_LegacyOoniClient._BUCKET, Delimiter='/', Prefix=_LegacyOoniClient._PREFIX,
                                   StartAfter=f'{_LegacyOoniClient._PREFIX}{first_date.strftime("%Y-%m-%d")}')
        for page in pages:
            self.num_list_requests += 1
            for entry in page.get('CommonPrefixes', []):
                date_dir = entry['Prefix']
                date_str = posixpath.basename(posixpath.dirname(date_dir))
                date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
                if date > last_date:
                    return
                for file_entry in self._list_files_with_index(date_dir, test_type, country):
                    url = SplitResult('s3', _LegacyOoniClient._BUCKET, f'{_LegacyOoniClient._PREFIX}{file_entry["filename"]}', None, None)
                    yield FileEntry(lambda: self._get_measurements(file_entry), test_type, country, date, url, _LegacyOoniClient._frame_bytes(file_entry['frames']))

    def _list_files_with_index(self, date_dir: str, test_type: str, country: str) -> Iterable[Dict]:
        s3_object = self._s3_client.get_object(
            Bucket=_LegacyOoniClient._BUCKET, Key=f'{date_dir}index.json.gz')
        self.num_get_requests += 1
        self.bytes_downloaded += s3_object['ContentLength']
        with gzip.open(s3_object['Body'], mode='rt', encoding='utf8') as json_lines:
            yield from _LegacyOoniClient._files_from_index(json_lines, test_type, country)

    def _get_measurements(self, file_entry: Dict) -> Iterable[Dict]:
        s3_key = f'{_LegacyOoniClient._PREFIX}{file_entry["filename"]}'
        frames = file_entry['frames']
        fi = 0
        while fi < len(frames):
            # We merge adjacent frames into segments to reduce the number of requests.
            segment_start = frames[fi]['file_off']
            segment_end = segment_start
            segment = []
            while fi < len(frames) and frames[fi]['file_off'] == segment_end:
                segment_end += frames[fi]['file_size']
                segment.append(frames[fi])
                fi += 1
            stream = self._s3_client.get_object(
                Bucket=_LegacyOoniClient._BUCKET, Key=s3_key, Range=f'{segment_start}-{segment_end - 1}')['Body']
            self.num_get_requests += 1
            self.bytes_downloaded += segment_end - segment_start
            with lz4.frame.LZ4FrameFile(stream, mode='r') as lz4_file:
                bytes_read = 0
                for frame in segment:
                    for entry in frame['data']:
                        skip = entry['text_off'] - bytes_read
                        if skip > 0:
                            lz4_file.read(skip)
                        measurement_str = lz4_file.read(size=entry['text_size'])
                        bytes_read = entry['text_off'] + entry['text_size']
                        yield ujson.loads(measurement_str)
