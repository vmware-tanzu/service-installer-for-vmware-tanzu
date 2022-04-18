from setuptools import setup

setup(
    name='arcas',
    version='1.1.1-1.5.1',
    packages=['src'],
    entry_points={
        'console_scripts': [
            'arcas = src.cli:main'
        ]
    })
