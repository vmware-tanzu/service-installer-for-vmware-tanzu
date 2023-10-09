from setuptools import setup

setup(name="arcas", version="2.4.0", packages=["src"], entry_points={"console_scripts": ["arcas = src.cli:main"]})
