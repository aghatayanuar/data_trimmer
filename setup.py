from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in data_trimmer/__init__.py
from data_trimmer import __version__ as version

setup(
	name="data_trimmer",
	version=version,
	description="Move Old Data To Archive Table",
	author="DAS",
	author_email="das@digitalasiasolusindo.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
