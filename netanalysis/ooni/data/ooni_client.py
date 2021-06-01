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
from typing import IO, Iterable
from urllib.parse import urlunsplit, SplitResult

import boto3
from botocore import UNSIGNED
from botocore.config import Config
import ujson

# TODO:
# - Add comments
# - Support old measurements
class FileEntry:
    """Represents a file entry in the OONI S3 Bucket."""
    def __init__(self, s3_client, test_type: str, country: str, date: dt.date, url: SplitResult, size: int) -> None:
        self._s3_client = s3_client
        self.test_type = test_type
        self.country = country
        self.date = date
        self.url = url
        self.size = size

    def get_measurements(self) -> Iterable[object]:
        """Gets an iterator for all the measurements in the file."""
        with closing(self._s3_client.get_object(Bucket=self.url.netloc, Key=self.url.path)['Body']) as remote_file, \
             gzip.GzipFile(fileobj=remote_file, mode='r') as source_file:
            for line in source_file:
                yield ujson.loads(line)


# Example files: `aws --no-sign-request s3 ls s3://ooni-data-eu-fra/raw/20210526/00/VE/webconnectivity/`
# First directory in the new bucket is 20201020/
class OoniClient:
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
                            file_path = PosixPath(key)
                            if file_path.name.endswith('.jsonl.gz'):
                                file_test_type = file_path.parent.name
                                url = SplitResult('s3', self._bucket, key, None, None)
                                yield FileEntry(self._client, file_test_type, country, date, url, entry['Size'])
    
    def _get_file(self, filename: PosixPath):
        key = f'{self._prefix}{filename}'
        return self._client.get_object(Bucket=self._bucket, Key=key)['Body']