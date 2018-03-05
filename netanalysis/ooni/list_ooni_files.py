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
import pathlib
import sys
import tarfile
from typing import Iterable, TextIO, Tuple

import boto3
from botocore.handlers import disable_signing
import botocore.response
import lz4.frame

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(name="list_ooni_files")  # type: logging.Logger

def read_report_files(ooni_bucket, test_name="web_connectivity", prefix="") -> Iterable[Tuple[str, TextIO]]:
    """
    Returns a pair (<filename>, <fileobj>) for each OONI report file.

    This generator takes care of navigating the hybrid structure in the OONI dataset.
    """
    REPORTS_ROOT = pathlib.PurePosixPath("autoclaved/jsonl.tar.lz4")
    for s3_obj in ooni_bucket.objects.filter(Prefix=str(REPORTS_ROOT / prefix)):
        report_path = pathlib.PurePosixPath(s3_obj.key).relative_to(REPORTS_ROOT)
        LOGGER.debug("Found S3 file %s", s3_obj.key)
        if test_name and (test_name not in report_path.name):
            continue
        report_file = s3_obj.get()["Body"]  # type: botocore.response.StreamingBody
        if report_path.suffix == ".lz4":
            report_path = report_path.with_name(report_path.stem)
            report_file = lz4.frame.open(report_file, "r")
        with report_file:
            if report_path.suffix == ".tar":
                with tarfile.open(fileobj=report_file, mode="r|") as tar_file:
                    for entry in tar_file:
                        yield entry.name, tar_file.extractfile(entry)
            else:
                yield str(report_path), report_file


def main(args):
    LOGGER.setLevel(logging.DEBUG if args.debug else logging.INFO)
    LOGGER.debug("Initializing Boto")
    # See https://ooni.torproject.org/post/mining-ooni-data/
    s3 = boto3.resource("s3")  # type: boto3.resources.base.ServiceResource
    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
    bucket = s3.Bucket("ooni-data")
    for filename, fileobj in itertools.islice(read_report_files(
            bucket, test_name=args.test_name, prefix=args.prefix), args.limit):
        with fileobj:
            # TODO: trim measurements
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug("Reading %s" % filename)
                print("  %s" % fileobj.read(80))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "List OONI files")
    parser.add_argument("--ooni_measurements", type=str, required=True)
    parser.add_argument("--test_name", type=str, default="web_connectivity")
    parser.add_argument("--prefix", type=str, default="")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--debug", action="store_true")
    sys.exit(main(parser.parse_args()))
