from setuptools import setup

setup(
    name='arcas',
    version='1.4-1.6.0',
    packages=['src'],
    entry_points={
        'console_scripts': [
            'arcas = src.cli:main'
        ]
    })
