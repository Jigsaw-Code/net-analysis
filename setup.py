import os
import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

deps = os.popen('pip freeze').readlines()
# readlines() doesn't strip trailing newlines
deps = [d.strip() for d in deps]

setuptools.setup(
    name="net-analysis",
    version="0.0.1",
    author="Jigsaw Operations, LLC",
    author_email="fortuna@google.com",
    description="Network censorship detection tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jigsaw-Code/net-analysis",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Networking :: Monitoring"
    ],
    python_requires='>=3.7',
    install_requires=deps
)
