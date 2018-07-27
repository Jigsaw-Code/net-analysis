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

# pylint: disable=yield-inside-async-function

import abc
import asyncio
from collections import deque
from concurrent.futures import Executor
from functools import singledispatch
import logging
import os
import os.path
from typing import Any, AsyncIterable, Dict, Iterable, List
from urllib.parse import urlencode, quote

import aiohttp
import ujson as json


class OoniClient(abc.ABC):
    @abc.abstractmethod
    async def get_measurement(self, measurement_id: str) -> Dict:
        pass

    @abc.abstractmethod
    def list_measurements(self, country_code: str, url: str) -> AsyncIterable[Dict]:
        pass


def _read_json_from_file(filename):
    with open(filename, mode="r") as file:
        return json.load(file)


def _write_json_to_file(json_object, filename):
    with open(filename, mode="w+") as file:
        return json.dump(json_object, file)


class CachedOoniClient(OoniClient):
    def __init__(self, origin: OoniClient, cache_dir: str, executor: Executor) -> None:
        self._origin = origin
        self._cache_dir = cache_dir
        self._executor = executor
        os.makedirs(os.path.join(cache_dir, "measurement"), exist_ok=True)

    async def _run_async(self, *args):
        return await asyncio.get_event_loop().run_in_executor(self._executor, *args)

    async def get_measurement(self, measurement_id: str):
        measurement_filename = os.path.join(
            self._cache_dir, "measurement", "%s.json" % measurement_id)
        logging.debug("Look up measurement %s", measurement_id)
        try:
            measurement = await self._run_async(_read_json_from_file, measurement_filename)
            logging.debug("Cache hit for measurement %s", measurement_id)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            logging.debug("Cache miss for measurement %s", measurement_id)
            measurement = await self._origin.get_measurement(measurement_id)
            await self._run_async(_write_json_to_file, measurement, measurement_filename)
        return measurement

    def list_measurements(self, *args, **kwargs) -> AsyncIterable[Dict]:
        return self._origin.list_measurements(*args, **kwargs)


@singledispatch
def _trim_json(json_obj, max_string_size: int):
    return json_obj


@_trim_json.register(dict)
def _(json_dict: dict, max_string_size: int):
    keys_to_delete = []  # type: str
    for key, value in json_dict.items():
        if type(value) == str and len(value) > max_string_size:
            keys_to_delete.append(key)
        else:
            _trim_json(value, max_string_size)
    for key in keys_to_delete:
        del json_dict[key]
    return json_dict


@_trim_json.register(list)
def _(json_list: list, max_string_size: int):
    for item in json_list:
        _trim_json(item, max_string_size)
    return json_list


# Documentation: https://api.ooni.io/api/
class ApiOoniClient(OoniClient):
    def __init__(self, api_url: str, http_client: aiohttp.ClientSession, max_string_size=1000) -> None:
        self._api_url = api_url
        self._http_client = http_client
        self._max_string_size = max_string_size

    async def _get_json(self, url):
        try:
            logging.debug("Fetching %s", url)
            async with self._http_client.get(url) as response:
                json_obj = await response.json(encoding="utf8")
                if self._max_string_size:
                    _trim_json(json_obj, self._max_string_size)
                return json_obj
        except Exception as error:
            raise Exception("Failed to query url %s" % url, error)

    def _api_query_url(self, path, params=None):
        query_url = "%s/%s" % (self._api_url, quote(path))
        if params:
            query_url = query_url + "?" + urlencode(params)
        return query_url

    async def get_measurement(self, measurement_id: str):
        logging.debug("Fetching measurement %s", measurement_id)
        measurement = await self._get_json(self._api_query_url("measurement/%s" % measurement_id))
        return measurement

    async def list_measurements(self, country_code: str=None, url: str=None):
        # Params order_by and input make the query *a lot* slower.
        # TODO: Consider fetching without input.
        # Unfortunately pagination breaks without order_by
        params = {
            "test_name": "web_connectivity",
            "order_by": "test_start_time",
            "order": "desc",
            "limit": 1000,
        }
        if country_code:
            params["probe_cc"] = country_code
        if url:
            params["input"] = url
            params["limit"] = 100

        next_page_url = self._api_query_url("measurements", params)
        measurement_entries = deque()
        while True:
            if not measurement_entries:
                if not next_page_url:
                    return
                logging.debug("Fetching %s", next_page_url)
                async with self._http_client.get(next_page_url) as response:
                    response_json = await response.json(encoding="utf8")
                next_page_url = response_json["metadata"].get("next_url")
                measurement_entries.extend(response_json["results"])
            if measurement_entries:
                yield measurement_entries.popleft()


def CreatePublicApiOoniClient(http_client: aiohttp.ClientSession):
    return ApiOoniClient("https://api.ooni.io/api/v1", http_client)
