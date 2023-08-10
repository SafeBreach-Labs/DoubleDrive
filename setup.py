from setuptools import setup, find_packages

with open("requirements.txt") as f:
    required = f.read().splitlines()
setup(
    name="DoubleDrive", 
    version="1.0", 
    package_dir={"": "src"},  # Optional
    packages=find_packages(where="src"),  # Required
    install_requires=required)
