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

import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="jigsaw-net-analysis",
    version="0.1.0",
    author="Jigsaw Operations, LLC",
    description="Network analysis tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jigsaw-Code/net-analysis",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Networking :: Monitoring"
    ],
    python_requires='>=3.6.9',
    install_requires=[
        "aiodns",
        "aiohttp",
        "boto3",
        "cchardet",
        "certifi",
        "iso3166",
        "jupyter",
        "lz4",
        "networkx",
        "geoip2",
        "google-cloud-bigquery",
        "matplotlib",
        "pandas",
        "plotly",
        "pydot",
        "scipy",
        "statsmodels",
        "ujson"
    ],
    include_package_data=True,
)
