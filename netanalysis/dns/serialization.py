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

import datetime
from functools import singledispatch
from typing import Dict, List

import ujson as json

from netanalysis.dns import model


@singledispatch
def to_json(value):
    return value

@to_json.register(List)
def _(value):
    return [to_json(e) for e in value]

@to_json.register(model.IpAddressData)
def _(data):
    return {"ip": str(data.ip)}


@to_json.register(model.CnameData)
def _(data):
    return {"cname": data.cname}


@to_json.register(model.ResourceRecord)
def _(record):
    query_json = {}
    for field in ["name", "data", "ttl"]:
        value = getattr(record, field)
        if value is None:
            continue
        if field == "ttl":
            value = value.seconds
        query_json[field] = to_json(value)
    return query_json


@to_json.register(model.DnsMeasurement)
def _(measurement):
    measurement_json = {}
    for key, value in measurement.__dict__.items():
        if value is None:
            continue
        if key == "resolver_ip":
            value = str(value)
        measurement_json[key] = to_json(value)
    return measurement_json


def record_data_from_json(data_json: Dict) -> model.RecordData:
    if "ip" in data_json:
        return model.IpAddressData(data_json["ip"])
    elif "cname" in data_json:
        return model.CnameData(data_json["cname"])
    else:
        raise ValueError("Invalid RecordData json: %s" %
                            json.dumps(data_json))
    
def record_from_json(record_json: Dict) -> model.ResourceRecord:
    params = {}
    for key, value in record_json.items():
        if key == "data":
            value = record_data_from_json(value)
        elif key == "ttl":
            value = datetime.timedelta(seconds=value)
        if value is not None:
            params[key] = value
    return model.ResourceRecord(**params)


def measurement_from_json(measurement_json: Dict) -> model.DnsMeasurement:
    params = {}
    for key, value in measurement_json.items():
        if key == "time":
            value = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        elif key == "records":
            value = [record_from_json(r) for r in value]
        if value is not None:
            params[key] = value
    return model.DnsMeasurement(**params)
