from setuptools import setup
import os

# This setup.py is minimal and delegates to pyproject.toml
# The only reason to customize it is to handle special cases

# Ensure test samples directory exists
if not os.path.exists('tests/samples'):
    os.makedirs('tests/samples', exist_ok=True)

# Include test samples
setup(
    include_package_data=True,
    package_data={
        'enchant_cli': ['../../tests/samples/*.txt'],
    },
    data_files=[
        ('tests/samples', ['tests/samples/test_sample.txt']),
    ],
)
