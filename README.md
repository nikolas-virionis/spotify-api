# spotify-api

<img src='https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_CMYK_Green.png' width='60%'>

- [Setup](#setup)

- [OG Scripts](#og-scripts)

## Setup

### Requirements:
  - Python installed<br>
 The ideal version, to run the package is 3.8.x, the version in which the package was built over,<br> however,
 older versions of python 3 shouldn't have any issues, as the package does not use any <br> 
 fancy, new methods, not supported by older versions of Python 3.x
  - Network Connection<br>
 So that a wide range of songs can be analised, it is imperative to have a network connection, at least for the first time executing a script using this package
  - <strong>A fitting playlist</strong><br>
 The perfect use case for this package is that of one big playlist (500+ songs), which you feel like listening to some of them, then others but never all of them
 Still, in the first versions of this package, this playlist will have to have at least two of your favorite songs.
  - Patience<br>
 It may seem funny or a joke, but the first mapping process of the playlist to a local pandas DataFrame, it will take a good while, up to 2.5 to 3 second per song, at 20-40Mbps Internet connection, being in Latam. All these factors play a part in the time for it to load.
 Just to make it clear, cpu, ram, these will not help much, the issue is to have up to 5 different http requests per song, which make this take so long
  - Jupyter Notebook<br>
 Not exactly a requirement but it is advised that a jupyter notebook is used ( even more advised to use the vscode extension for jupyter notebooks ), because it is important, or at least more confortable, to have the variable still in memory and then decide how to use it, without having to run the script multiple times
  - Spotify access<br>
 I mean, you know that already, right?

  - Installing the package<br>
~~~ps1
pip install spotify-recommender
~~~


  - Importing the package<br>

Firstly, it's necessary to import the method start_api from the package spotify_recommender.api:
 ~~~ python
 from spotify_recommender.api import start_api
 ~~~







## OG Scripts
## Context
This script, in jupyter notebook format for organization purposes, applies the technique called K Nearest Neighbors to find the 50 closest songs to either one chosen or one of the users top 5(short term), all within a specific Spotify playlist, in order to maintain the most consistency in terms of the specific chosen style, and creates a new playlist with those songs in the user's library, using their genres, artists and overall popularity as metrics to determine indexes of comparison between songs

### Variations
There are also 2 variations from that, which consist of medium term favorites related top 100 and "short term top 5" related top 50 songs. They vary from OG model since the base song(s) is(are) not chosen by hand but statistically

## DISCLAIMER ##
Not fit for direct use since some information such as client id, client secret, both of which are, now, in a hidden script on .gitignore so that it is not made public, have to be informed in order for the Spotify Web API to work properly
And also, these scripts are deprecated, so they will not have any maintenance or overtime improvements
