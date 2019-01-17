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

import datetime
from typing import List

from netanalysis.traffic.data import model as traffic

class AnomalyPoint(object):
    """A single timeline point outside the expected range.
    
    Attributes:
      timestamp: The time of the anomaly
      traffic: The observed traffic number
      expected: What traffic number was expected
      absolute_impact: expected - traffic
      relative_impact: absolute_impact / mean traffic
    """

    def __init__(self, timestamp: datetime.datetime, traffic: float,
                 expected: float, relative_impact: float) -> None:
        self.timestamp = timestamp
        self.traffic = traffic
        self.expected = expected
        self.absolute_impact = self.expected - self.traffic
        self.relative_impact = relative_impact

    def __repr__(self) -> str:
        return "AnomalyPoint(%s)" % repr(self.__dict__)


class ProductDisruption(object):
    """ A disruption to a product represented by a sequence of anomalous points.

    This refers to a single region, which is implicit.

    Attributes:
      product_id: The ProductId of the product this disruption is about
      start: Time of the first anomaly point
      end: Time of the last anomaly point
      anomalies: List of all observed anomalies
      absolute_impact: Sum of the absolute impact of all anomalies
      relative_impact: Sum of the relative impact of all anomalies
    """

    def __init__(self, product_id: traffic.ProductId) -> None:
        self.product_id = product_id
        self.start = datetime.datetime.max
        self.end = datetime.datetime.min
        self.anomalies = []  # type: List[AnomalyPoint]
        self.absolute_impact = 0.0
        self.relative_impact = 0.0

    def add_anomaly(self, anomaly: AnomalyPoint) -> None:
        self.anomalies.append(anomaly)
        self.start = min(self.start, anomaly.timestamp)
        self.end = max(self.end, anomaly.timestamp)
        self.relative_impact += anomaly.relative_impact
        self.absolute_impact += anomaly.absolute_impact

    def __repr__(self) -> str:
        return "ProductDisruption(%s)" % repr(self.__dict__)


class RegionDisruption(object):
    """A disruption to traffic in a region.
    
    The region disruption is represented by overlapping disruptions of
    multiple products in that region.

    Attributes:
      region_code: The country code of the region this disruption is about.
      start: Time of the first anomaly point
      end: Time of the last anomaly point
      product_disruptions: The list of all observed ProductDisruptions
    """
    def __init__(self, region_code: str) -> None:
        self.region_code = region_code
        self.start = datetime.datetime.max
        self.end = datetime.datetime.min
        self.product_disruptions = []  # type: List[ProductDisruption]

    def add_product_disruption(self, product_disruption: ProductDisruption) -> None:
        self.product_disruptions.append(product_disruption)
        self.start = min(self.start, product_disruption.start)
        self.end = max(self.end, product_disruption.end)

    def __repr__(self) -> str:
        return "RegionDisruption(%s)" % repr(self.__dict__)
