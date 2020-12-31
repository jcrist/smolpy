import os
from setuptools import setup, find_packages

setup(
    name="smolpy",
    version="0.0.1",
    maintainer="Jim Crist-Harif",
    maintainer_email="jcristharif@gmail.com",
    url="https://jcristharif.com/smolpy/",
    description="A smol and safe python",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    license="BSD",
    packages=find_packages(),
    long_description=(
        open("README.rst", encoding="utf-8").read()
        if os.path.exists("README.rst")
        else ""
    ),
    python_requires=">=3.8",
    zip_safe=False,
)
