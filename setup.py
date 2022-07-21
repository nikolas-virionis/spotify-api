from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '3.3.0'
DESCRIPTION = 'Python package which takes the songs of a greater playlist as starting point to make recommendations of groups of songs that might bond well within that same playlist, using K-Nearest-Neighbors Technique'

# Setting up
setup(
    name="spotify_recommender_api",
    version=VERSION,
    author="Nikolas B Virionis",
    author_email="nikolas.virionis@bandtec.com.br",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    url="https://github.com/nikolas-virionis/spotify-api",
    packages=find_packages(),
    install_requires=['pandas', 'requests', 'seaborn', 'matplotlib'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires='>=3',
)
