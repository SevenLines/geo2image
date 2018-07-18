from setuptools import setup, find_packages
from os.path import join, dirname

setup(
    name='geo2image',
    version='0.0.1',
    license='MIT',
    packages=['geo2image'],
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    install_requires=['pycairo', 'mercantile', 'Pillow']
)
