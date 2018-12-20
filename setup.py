from setuptools import setup, find_packages

setup(
    name="dotter",
    version="0.0.1",
    description="A dotfile link farm manager",
    author="nonlogicaldev",
    url="https://github.com/NonLogicalDev/nld.cli.dotter",

    packages=find_packages(),
    scripts=["bin/dotter"]
)
