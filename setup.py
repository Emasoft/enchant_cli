from setuptools import setup

# This setup.py is minimal and delegates to pyproject.toml
# The only reason to customize it is to handle special cases

# Include test samples
setup(
    include_package_data=True,
    data_files=[
        ('tests/samples', ['tests/samples/test_sample.txt']),
    ],
)
