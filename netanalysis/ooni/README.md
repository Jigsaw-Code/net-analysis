# OONI Measurement Data

This directory contains libraries and tools to fetch [OONI data](https://ooni.org/data/).

## Fetch the measurement data

To fetch the last 14 days of data for a country into a `ooni_data/` directory:

    python -m netanalysis.ooni.data.fetch_measurements --country=BY --output_dir=./ooni_data/

If you call it a second time, it will redownload data already downloaded.

Use `--first_date and --last_date` to restrict the fetch to a specific, inclusive, date range. For example:

    python -m netanalysis.ooni.data.fetch_measurements --output_dir=./ooni_data/ --first_date=2021-01-01 --last_date=2021-01-31

By default the tool will drop any measurement field that are longer than 1000 characters in order to save space. You can change that dy setting a different value for `--max_string_size`.

The tool also stops fetching data after if downloads enough data to cost OONI an estimated $1.00 USD in order to prevent accidental costs. You can override that with `--cost_limit_usd`.
