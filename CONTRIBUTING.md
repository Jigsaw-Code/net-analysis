# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution,
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

## Wishlist

Here are some things we'd like to see implemented:

* Scalable and reproducible OONI data fetch
  * Fetch data from their Amazon S3 bucket ([info](https://ooni.torproject.org/post/mining-ooni-data/))
  * Store OONI data in a compact and queriable format. Consider [Parquet](https://pypi.python.org/pypi/parquet) or [Avro](https://github.com/tebeka/fastavro).
  * Use Apache Spark to pre-process data on the cloud to significantly reduce and speed up data transfer.

* Enhance analysis
  * Provide site-level analysis with timeline and high-level explanations.
  * Provide country-level analysis, listing measured sites, and explaining types of interference found.
    * Collect a list of blackhole IPs that each country uses.

* Make analysis accessible to non-technical people
  * Create a web application with analysis that non-technical people can undertand. Can piggyback on the analysis from the AnalyzeDomain notebook.

* Scale Analysis
  * Figure our a way to classify every edge in the DNS graph in batch, rather than on-demand.
  * Create or consume a IP -> TLS certificate data source to minimize connections for the TLS validation.

* Add new DNS data sources
  * Include [DNS queries from Satellite](https://scans.io/study/washington-dns). Explore other sources.
