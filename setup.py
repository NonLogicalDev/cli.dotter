from setuptools import setup, find_packages
import time

from dotter.version import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="nl-dotter",
    version=__version__,
    url="https://github.com/NonLogicalDev/cli.dotter",
    license="MIT",

    author="nonlogicaldev",
    description="A dotfile link farm manager.",

    long_description=long_description,
    long_description_content_type="text/markdown",

    scripts=["bin/dotter"],

    packages=find_packages(),
    install_requires=[
        'dacite',
    ],
    keywords=[
        "dotfile", "link farm"
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
