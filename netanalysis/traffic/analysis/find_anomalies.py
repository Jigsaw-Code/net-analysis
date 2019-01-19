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

import argparse
import datetime
import logging
import sys
import time
from typing import List, Iterable
import urllib.parse

import iso3166
import pandas as pd
import statsmodels.api as sm

from netanalysis.traffic.analysis import model
import netanalysis.traffic.data.model as traffic
from netanalysis.traffic.data.file_repository import FileTrafficRepository

logging.getLogger().setLevel(logging.INFO)


def get_expectations_1(time_series: pd.Series) -> pd.DataFrame:
    # Sets frequency to 8 weeks.
    components = sm.tsa.seasonal_decompose(
        time_series, freq=7 * 4 * 2, model="additive", two_sided=False)
    expected = components.trend + components.seasonal
    max_delta = 3 * components.resid.std()
    lower_bound = expected - max_delta
    upper_bound = expected + max_delta
    return pd.DataFrame(index=time_series.index,
                        data={"expected": expected,
                              "lower_bound": lower_bound,
                              "upper_bound": upper_bound})


# def get_expectations_2(time_series):
#     # Sets frequency to 8 weeks.
#     components = sm.tsa.seasonal_decompose(
#         time_series, freq=7 * 4 * 2, model="additive", two_sided=False)
#     expected = components.trend + components.seasonal
#     window_days = 365
#     resid_median = components.resid.rolling(
#         center=False, window=window_days).median()
#     delta = 4 * 1.4826 * components.resid.rolling(window_days).apply(
#         lambda x: np.median(np.fabs(x - np.median(x))))
#     lower_bound = resid_median - delta
#     upper_bound = resid_median + delta
#     return pd.DataFrame({"expected": expected, "lower_bound": lower_bound, "upper_bound": upper_bound})


def find_anomalies(time_series: pd.Series) -> List[model.AnomalyPoint]:
    anomalies = []  # type: List[model.AnomalyPoint]
    expectations = get_expectations_1(time_series)
    anomalous_dates = (time_series <
                       expectations.lower_bound).loc[lambda e: e].index  # type: List[pd.Timestamp]
    mean_traffic = time_series.mean()
    for timestamp in anomalous_dates:
        relative_impact = (
            expectations.expected[timestamp] - time_series[timestamp]) / mean_traffic
        anomalies.append(model.AnomalyPoint(
            timestamp.to_pydatetime(), time_series[timestamp], expectations.expected[timestamp], relative_impact))
    return anomalies


def group_as_product_disruptions(product_id: traffic.ProductId,
                                 anomalies: Iterable[model.AnomalyPoint],
                                 max_time_delta: datetime.timedelta) -> List[model.ProductDisruption]:
    """Groups anomalies that are within the given max_time_delta"""
    disruptions = []  # type: List[model.ProductDisruption]
    current_disruption = None  # type: model.ProductDisruption
    disruption_end = datetime.datetime.min
    for anomaly in anomalies:
        if anomaly.timestamp > disruption_end + max_time_delta:
            current_disruption = model.ProductDisruption(product_id)
            disruptions.append(current_disruption)
        current_disruption.add_anomaly(anomaly)
        disruption_end = current_disruption.end
    return disruptions


def remove_minor_disruptions(product_disruptions: List[model.ProductDisruption]) -> List[model.ProductDisruption]:
    return [p for p in product_disruptions if p.relative_impact >= 1.0 and max(a.relative_impact for a in p.anomalies) >= 0.5]


def group_as_regional_disruptions(
        region_code: str,
        product_disruptions: List[model.ProductDisruption]) -> List[model.RegionDisruption]:
    region_disruptions = []  # type: List[model.RegionDisruption]
    current_region_disruption = None  # type: model.RegionDisruption
    disruption_end = datetime.datetime.min
    for product_disruption in sorted(product_disruptions, key=lambda d: d.start):
        if product_disruption.start > disruption_end:
            current_region_disruption = model.RegionDisruption(region_code)
            region_disruptions.append(current_region_disruption)
        current_region_disruption.add_product_disruption(product_disruption)
        disruption_end = current_region_disruption.end
    return region_disruptions


def _to_google_timestamp(timestamp: datetime.datetime):
    """Converts a datetime.datetime to the timestamp format used by the Transparency Report"""
    return int(time.mktime(timestamp.timetuple()) * 1000)


def _make_report_url(start_date: datetime.datetime, end_date: datetime.datetime, region_code: str, product_id: traffic.ProductId):
    """Creates a Transparency Report url"""
    # Align with the end of the day
    end_date = end_date + datetime.timedelta(days=1)
    chart_padding = (end_date - start_date) * 2
    chart_start_date = start_date - chart_padding
    chart_end_date = min(end_date + chart_padding, datetime.datetime.now())
    return ("https://transparencyreport.google.com/traffic/overview?%s" % 
       urllib.parse.urlencode({
           "lu": "fraction_traffic",
           "fraction_traffic": "product:%s;start:%s;end:%s;region:%s" % (
                product_id.value, _to_google_timestamp(chart_start_date),
                _to_google_timestamp(chart_end_date), region_code
            )
       })
    )


def _make_tor_users_url(start_date: datetime.datetime, end_date: datetime.datetime, region_code: str):
    end_date = end_date + datetime.timedelta(days=1)
    chart_padding = max(datetime.timedelta(days=7), (end_date - start_date) * 2)
    chart_start_date = start_date - chart_padding
    chart_end_date = min(end_date + chart_padding, datetime.datetime.now())
    return ("https://metrics.torproject.org/userstats-relay-country.html?%s" %
        urllib.parse.urlencode({
            "events": "on",
            "start": chart_start_date.date().isoformat(),
            "end": chart_end_date.date().isoformat(),
            "country": region_code.lower()
        })
    )

def _make_context_web_search_url(start_date: datetime.datetime, end_date: datetime.datetime, region_code: str):
    return ("https://www.google.com/search?%s" %
        urllib.parse.urlencode({
            "q": "internet %s" % iso3166.countries.get(region_code).name,
            "tbs": "cdr:1,cd_min:%s,cd_max:%s" % (
                start_date.date().strftime("%m/%d/%Y"),
                end_date.date().strftime("%m/%d/%Y")
            )
        })
    )


def _make_context_twitter_url(start_date: datetime.datetime, end_date: datetime.datetime, region_code: str):
    return ("https://twitter.com/search?%s" %
        urllib.parse.urlencode({
            "q": "internet %s since:%s until:%s" % (
                iso3166.countries.get(region_code).name,
                start_date.date().isoformat(),
                end_date.date().isoformat()
            )
        })
    )


def print_disruption_csv(disruption: model.RegionDisruption) -> None:
    country_name = iso3166.countries.get(disruption.region_code).name
    search_url = _make_context_web_search_url(disruption.start,
        disruption.start + datetime.timedelta(days=7),
        disruption.region_code)
    twitter_url = _make_context_twitter_url(disruption.start,
        disruption.start + datetime.timedelta(days=7),
        disruption.region_code)
    tor_url = _make_tor_users_url(disruption.start, disruption.end, disruption.region_code)
    print("%s (%s) %s %s Context: %s %s %s" % (
        country_name, disruption.region_code, disruption.start.date().isoformat(),
        disruption.end.date().isoformat(),
        search_url, twitter_url, tor_url
    ))
    for product_disruption in disruption.product_disruptions:
        report_url = _make_report_url(
            product_disruption.start, product_disruption.end, disruption.region_code, product_disruption.product_id)
        print("    %s, %s, %s, %f, %f, %s" % (
            product_disruption.product_id.name,
            product_disruption.start.date(),
            product_disruption.end.date(),
            product_disruption.relative_impact,
            product_disruption.absolute_impact,
            report_url,
        ))
    # return
    # report_url = _make_report_url(
    #     disruption.start, disruption.end, disruption.region_code, product_id)
    # print("%s,%s,%s,%s,%s,%f,%f,%s" % (
    #     disruption.start.date().isoformat(), disruption.end.date().isoformat(),
    #     disruption.region_code, disruption.product_id.value,
    #     disruption.product_id.name, disruption.relative_impact,
    #     disruption.absolute_impact, report_url))


def find_all_disruptions(repo: traffic.TrafficRepository,
                         regions: Iterable[str], products: Iterable[traffic.ProductId]) -> List[model.RegionDisruption]:
    """Returns a list of all region disruptions for the given regions and analyzing the given products only."""
    # TODO: Investigate why YouTube is not output for these outages:
    # TG 2017-09-20 2017-09-21
    #     BLOGGER, 2017-09-20, 2017-09-21, 2.085934, 0.115080, https://transparencyreport.google.com/traffic/overview?lu=fraction_traffic&fraction_traffic=product:2;start:1505534400000;end:1506398400000;region:TG
    #     WEB_SEARCH, 2017-09-20, 2017-09-21, 1.388299, 0.223981, https://transparencyreport.google.com/traffic/overview?lu=fraction_traffic&fraction_traffic=product:19;start:1505534400000;end:1506398400000;region:TG
    # ET 2017-05-31 2017-06-07
    #     TRANSLATE, 2017-05-31, 2017-06-02, 2.786339, 0.203082, https://transparencyreport.google.com/traffic/overview?lu=fraction_traffic&fraction_traffic=product:16;start:1495684800000;end:1496980800000;region:ET
    #     WEB_SEARCH, 2017-05-31, 2017-06-07, 5.233837, 1.615268, https://transparencyreport.google.com/traffic/overview?lu=fraction_traffic&fraction_traffic=product:19;start:1494820800000;end:1498276800000;region:ET

    all_disruptions = []  # type: List[model.RegionDisruption]
    for region_code in regions:
        product_disruptions = []  # type: List[model.ProductDisruption]
        for product_id in products:
            try:
                if product_id == traffic.ProductId.UNKNOWN:
                    continue
                logging.info("Processing region %s product %s",
                                region_code, product_id.name)

                full_time_series = repo.get_traffic(region_code, product_id)
                if full_time_series.empty:
                    logging.info(
                        "Empty time series for region %s product %s", region_code, product_id.name)
                    continue

                daily_time_series = full_time_series.resample("D").mean()
                anomalies = find_anomalies(daily_time_series)
                if not anomalies:
                    logging.info("Found no anomalies")
                    continue
                grouped_disruptions = group_as_product_disruptions(
                    product_id, anomalies, datetime.timedelta(days=3))
                major_grouped_disruptions = remove_minor_disruptions(
                    grouped_disruptions)
                logging.info("Found %d major product disruptions from %d disruptions and %d anomalies",
                                len(major_grouped_disruptions), len(grouped_disruptions), len(anomalies))
                product_disruptions.extend(major_grouped_disruptions)
            except Exception as error:
                logging.info("Error processing region %s, product %s: %s", region_code, product_id.name, str(error))
        region_disruptions = group_as_regional_disruptions(
            region_code, product_disruptions)
        logging.info("Found %d region disruptions from %d product disruptions for %s", len(
            region_disruptions), len(product_disruptions), region_code)
        all_disruptions.extend(region_disruptions)
    return all_disruptions


def main(args):
    repo = FileTrafficRepository(args.traffic_data)
    if args.products:
        product_id_list = [traffic.ProductId[ps.strip().upper()] for ps in args.products.split(",")]
    else:
        product_id_list = [p for p in traffic.ProductId if p.value != traffic.ProductId.UNKNOWN]

    try:
        all_disruptions = find_all_disruptions(
            repo, repo.list_regions(), product_id_list)  # type: List[RegionDisruption]
    except KeyboardInterrupt:
        pass

    logging.info("Found %d total region disruptions", len(all_disruptions))
    all_disruptions.sort(reverse=True, key=lambda d: (d.start, d.end))
    for region_disruption in all_disruptions:
        print_disruption_csv(region_disruption)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Finds anomalies in traffic data")
    parser.add_argument("--traffic_data", type=str, required=True, help="The base directory of the traffic data")
    parser.add_argument("--products", type=str,
        help="Comma-separated list of the products to analyze")
    sys.exit(main(parser.parse_args()))
