from setuptools import setup

with open("./README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='spotify-recommender',
    version='1.0.0',
    description='The number-utility module makes it simple for you to do number manipulation and perform various operations on numbers.',
    py_modules=["spotify-recommender"],
    package_dir={'': 'src'},
    requires=['pandas', 'requests', 'operator', 'json'],
    extras_require={
        "dev": [
            "pytest >= 3.7",
            "check-manifest",
            "twine"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Nikolas Virionis",
    author_email="nikolas.virionis@bandtec.com.br",
    url="https://github.com/nikolas-virionis/spotify-api"
)