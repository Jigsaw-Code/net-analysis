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

import itertools

import boto3
from botocore.handlers import disable_signing


s3 = boto3.resource("s3")
s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
bucket = s3.Bucket("ooni-data")
for obj in itertools.islice(bucket.objects.filter(Prefix="autoclaved/jsonl.tar.lz4/2017-11-10/"), 1000):
    print(obj)
# objects = s3.list_objects_v2(Bucket="ooni-data", Prefix="autoclaved/jsonl.tar.lz4/2017-11-10/")
# print(objects)
