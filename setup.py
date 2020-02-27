import os
import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

packages = setuptools.find_packages()
print(", ".join(packages))
# exit()

setuptools.setup(
    name="jigsaw-net-analysis",
    version="0.0.1",
    author="Jigsaw Operations, LLC",
    description="Network analysis tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jigsaw-Code/net-analysis",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Networking :: Monitoring"
    ],
    python_requires='>=3.7',
    install_requires=[ 
        "aiodns",
        "aiohttp",
        "boto3",
        "cchardet",
        "certifi",
        "iso3166",
        "jupyter",
        "networkx",
        "geoip2",
        "google-cloud-bigquery",
        "matplotlib",
        "pandas",
        "plotly",
        "pydot",
        "scipy",
        "statsmodels",
        "ujson"],
)
