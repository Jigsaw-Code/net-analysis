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
import itertools
import logging
import os.path
import sys
import tarfile

import boto3
from botocore.handlers import disable_signing
from botocore.response import StreamingBody
import lz4.frame

def list_files(bucket, test_name="web_connectivity", prefix=""):
    for obj in bucket.objects.filter(Prefix="autoclaved/jsonl.tar.lz4/" + prefix):
        filename = obj.key.rsplit("/", 1)[-1]
        if not test_name or test_name in filename:
            yield obj
   

def main(args):
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    # See https://ooni.torproject.org/post/mining-ooni-data/
    s3 = boto3.resource("s3")  # type: boto3.session.Session.resource
    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
    bucket = s3.Bucket("ooni-data")
    for obj in itertools.islice(list_files(bucket, test_name=args.test_name, prefix=args.prefix), args.limit):
        print("Fetching %s" % obj.key)
        # TODO: Handle .tar.lz4 files
        obj_body = obj.get()["Body"]  # type: botocore.response.StreamingBody
        with lz4.frame.open(obj_body, "r") as obj_file:
            if obj.key.endswith(".tar.lz4"):
                with tarfile.open(fileobj=obj_file, mode="r|") as tar_file:
                    tar_file.list()
            else:
                # TODO: trim measurements
                print(obj_file.read(100))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "List OONI files")
    parser.add_argument("--ooni_measurements", type=str, required=True)
    parser.add_argument("--test_name", type=str, default="web_connectivity")
    parser.add_argument("--prefix", type=str, default="")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--debug", action="store_true")
    sys.exit(main(parser.parse_args()))
