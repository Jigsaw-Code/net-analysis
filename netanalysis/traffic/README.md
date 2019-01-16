# Google Traffic Data

This directory contains libraries and tools to fetch the [Google Transparency Report traffic data](https://transparencyreport.google.com/traffic/overview).
Note that each time-series is normalized, with added noise. They are not the actual traffic numbers.

## API Usage Notice

Before using this code, you must agree to [Google APIs Terms of Service](https://developers.google.com/terms/).

This code fetches data from an unsupported and undocumented API used by Google's Transparency Report and may break at any time without notice.

We expect this repository to be a centralized location where the community can update the code if the API changes.

## Fetching the data

To fetch the data into a `traffic_data/` directory:

    .venv/bin/python -m netanalysis.traffic.fetch_google_traffic --output_dir=traffic_data/

If you call it a second time, it will skip data already downloaded. Delete the output directory if you want the data to be fetched again.

Use `--products` to restrict the fetch to specific products. For example:

    .venv/bin/python -m netanalysis.traffic.fetch_google_traffic --output_dir=traffic_data/ --products=BLOGGER,GROUPS,SITES,TRANSLATE,WEB_SEARCH,YOUTUBE

You can find the list of products at [transparency_report.py](transparency_report.py).
