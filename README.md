# Tools for Network Analysis

This repository contains tools, libraries and applications to analyze network measurements.

_Disclaimer: This is not an officially supported Jigsaw product._


> **Experimental code.** We may break you. Please let us know if you are using this code.

## Requirements

[Set up your Python development environment](python_env.md)


## Tutorials

### Analyze DNS Measurements

[Analyze DNS Queries](netanalysis/analysis/analyze_dns.md) describes how to fetch data from OONI and check for interference.

[netanalysis/analysis/DomainAnalysis.ipynb](netanalysis/analysis/DomainAnalysis.ipynb) gives you an idea of what the analysis look like.

### Get information about an IP address:

```
.venv/bin/python -m netanalysis.ip.info 8.8.8.8
```

### Check if an IP is valid for a domain:

```
.venv/bin/python -m netanalysis.dns.domain_ip_validator jigsaw.google.com 172.217.10.78
```

## Contributing

We welcome your contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details and wishlist.
