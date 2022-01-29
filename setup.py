from setuptools import setup

with open("./README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='spotify_recommender',
    version='2.0.3',
    description='Python package which takes the songs of a greater playlist as starting point to make recommendations of songs based on up to 5 specific songs within that playlist, using K-Nearest-Neighbors Technique',
    py_modules=["spotify_recommender"],
    package_dir={'src': 'src'},
    requires=['pandas', 'requests', 'webbrowser',],
    install_requires=['pandas', 'requests', 'webbrowser',],
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
