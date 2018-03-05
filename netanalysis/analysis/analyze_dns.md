# Analyze DNS Queries

In this example, we will fetch measurements for `www.youtube.com` from OONI and analyze them.

## Pre-requisites

[Set up your Python environment](../../python_env.md)

## Fetch measurements

Run

```
time .venv/bin/python -m netanalysis.ooni.fetch_measurements --debug --output_dir=ooni_data --country=* --url=www.youtube.com --num_measurements=1000
```

This will take in the order of 10 minutes (the OONI API is not designed for batch processing). Measurements will be written as files in  `ooni_data/<domain>/<country>/<measurement_id>`.

## Convert to DNS resource records

Run
```
time .venv/bin/python -m netanalysis.ooni.measurements_to_dns_records --ooni_measurements_dir=ooni_data/
```

This will create `ooni_data/dns_records.json` with all the DNS records.

## Analyze data

Run

```
.venv/bin/jupyter notebook
```

And open the Jupyter Notebook `notebooks/netanalysis/analysis/DomainAnalysis.ipynb`.

That notebook will allow you to explore the DNS data and analyze possible interference.
