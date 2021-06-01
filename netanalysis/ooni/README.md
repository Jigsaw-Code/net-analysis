# OONI Measurement Data

This directory contains libraries and tools to fetch [OONI data](https://ooni.org/data/). This tool only supports access to the mesurements on the new `ooni-data-eu-fra` OONI S3 bucket, which started to be populated on 2020-10-20. Support for the old data is a to do.

## Fetch the measurement data

To fetch the last 14 days of data for a country into a `ooni_data/` directory:

    python -m netanalysis.ooni.data.fetch_measurements --country=BY --output_dir=./ooni_data/

If you call it a second time, it will redownload data already downloaded.

Use `--first_date` and `--last_date` to restrict the fetch to a specific, inclusive, date range. For example:

    python -m netanalysis.ooni.data.fetch_measurements --output_dir=./ooni_data/ --country=BY --first_date=2021-01-01 --last_date=2021-01-31

### Data trimming
By default the tool will drop any measurement field that are longer than 1000 characters in order to save space. You can change that by passing a different value for `--max_string_size`.

This is primarily intended to drop the response bodies, which are often not needed and take most of the space. For the date range example above, we download 158 MiB of data, but only store 18 MiB after the trimming, a nearly 9x difference!

### Test types
By default the tool will download `webconnectivity` tests only. You can select a different test type with `--test_type`.

### Cost limit
The tool also stops fetching data after if downloads enough data to cost OONI an estimated $1.00 USD in order to prevent accidental costs. You can override that with `--cost_limit_usd`.

## Direct S3 access

You can use the aws cli to access the bucket. For example:
```
aws --no-sign-request s3 ls s3://ooni-data-eu-fra/raw/20210526/00/VE/webconnectivity/
```

However there's no way to easily select a country, measurement type or date range.