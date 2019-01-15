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

"""
Model for traffic data repositories.
"""
import abc
import datetime
from enum import IntEnum
from typing import Iterable, Tuple

import pandas as pd

class ProductId(IntEnum):
    UNKNOWN = 0
    ALL = 1
    BLOGGER = 2
    BOOKS = 3
    DOCS = 4
    EARTH = 5
    GMAIL = 6
    GROUPS = 7
    IMAGES = 8
    MAPS = 9
    ORKUT = 11
    PICASA_WEB_ALBUMS = 12
    SITES = 14
    SPREADSHEETS = 15
    TRANSLATE = 16
    VIDEOS = 18
    WEB_SEARCH = 19
    YOUTUBE = 21


class TrafficRepository(abc.ABC):
    @abc.abstractmethod
    def list_regions(self) -> Iterable[str]:
        pass

    @abc.abstractmethod
    def get_traffic(self, region_code: str, product_id: ProductId,
                    start: datetime.datetime = None, end: datetime.datetime = None
                   ) -> pd.Series:
        pass
