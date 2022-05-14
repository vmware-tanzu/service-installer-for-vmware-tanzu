from setuptools import setup

setup(
    name='arcas',
    version='1.2-1.5.3',
    packages=['src'],
    entry_points={
        'console_scripts': [
            'arcas = src.cli:main'
        ]
    })
