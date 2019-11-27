from setuptools import setup, find_packages

setup(
    name="nl-dotter",
    version="0.0.1",
    licensce="MIT",

    author="nonlogicaldev",
    description="A dotfile link farm manager.",

    url="https://github.com/NonLogicalDev/cli.dotter",

    scripts=["bin/dotter"],

    packages=find_packages(),

    keywords=[
        "dotfile", "link farm"
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
