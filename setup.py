from setuptools import setup

setup(
    name='arcas',
    version='1.3-1.5.4',
    packages=['src'],
    entry_points={
        'console_scripts': [
            'arcas = src.cli:main'
        ]
    })
