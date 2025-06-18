#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from pathlib import Path

setup(
    name='enchant-book-manager',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'beautifulsoup4>=4.13.4',
        'chardet>=5.2.0',
        'colorama>=0.4.6',
        'peewee>=3.18.1',
        'pyyaml>=6.0.2',
        'regex>=2024.11.6',
        'requests>=2.32.3',
        'rich>=14.0.0',
        'tenacity>=9.1.2',
    ],
    entry_points={
        'console_scripts': [
            'enchant-cli=enchant_cli:main',
            'cli-translator=cli_translator:main',
        ],
    },
    author='Emasoft',
    author_email='713559+Emasoft@users.noreply.github.com',
    description='EnChANT - English-Chinese Automatic Novel Translator: A comprehensive Chinese novel translation and EPUB generation system',
    long_description=open('ENCHANT_README.md').read() if Path('ENCHANT_README.md').exists() else '',
    long_description_content_type='text/markdown',
    url='https://github.com/Emasoft/ENCHANT_BOOK_MANAGER',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Text Processing :: Linguistic',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.8',
)
