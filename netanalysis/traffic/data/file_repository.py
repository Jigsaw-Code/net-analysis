#!/usr/bin/python
#
# Copyright 2019 Jigsaw Operations LLC
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

import os
from typing import Iterable

import pandas as pd

from netanalysis.traffic.data import model


class FileTrafficRepository(model.TrafficRepository):
    """TrafficRepository that reads the traffic data from previously downloaded files"""

    def __init__(self, base_directory: str) -> None:
        self.base_directory = base_directory

    def list_regions(self) -> Iterable[str]:
        return sorted(os.listdir(self.base_directory))

    def get_traffic(self, region_code: str, product_id: model.ProductId) -> pd.Series:
        filename = os.path.join(self.base_directory, region_code, "%s.csv" % product_id.name)
        try:
            return pd.read_csv(filename, parse_dates=True, squeeze=True,
                               index_col="timestamp", names=["timestamp", "traffic"])
        except FileNotFoundError:
            return pd.DataFrame()
