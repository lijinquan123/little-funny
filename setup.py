# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2023/10/10 16:01
# @Version     : Python 3.6.4
import json
from pathlib import Path

from setuptools import find_packages, setup

VERSION_PATH = Path(__file__).parent / 'version.json'
version, description = json.loads(VERSION_PATH.read_text("utf-8"))
__version__ = f'1.0.{int(version)}'
setup(
    name='Little Funny',
    version=__version__,
    url='',
    license='None',
    author='LJQ',
    install_requires=[],
    dependency_links=[],
    description='little funny',
    long_description='little but useful tools!',
    packages=find_packages(),
    platforms='any',
    entry_points={
        'console_scripts': [
            'md5creator=utils.md5creator:main',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    extras_require={},
    zip_safe=False
)
