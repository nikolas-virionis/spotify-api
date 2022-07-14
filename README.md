# spotify-recommender

<img src='./readme-pictures/Spotify Logo.png' width='60%'>

- [Use Case](#use-case)
- [Setup](#setup)
- [Methods](#methods)
- [Packages used](#packages-used)
- [OG Scripts](#og-scripts)
- [Contribution Rules](#contributing)


## Use Case
 - This is the first section of this readme, because, you will see, this package can help, but nothing is perfect, so it will, as long as you fit in this very, very, particular use case ;(
 - The perfect use case for this is that one playlist (or more) that you put a bunch of songs in different times and mood styles, and when you listen to it, you feel like only listening to a part of it, some days later, that part is useless, but some other part is awesome. The big issue here is that those "parts" are shuffled all across the playlist. Then how would one find those songs that they are craving for, today, tomorrow, and later? Speaking from experience, it is not worth it to map manually a 1000 song playlist and filter out 50, or 100.
 - This package comes to solve this issue, roughly, because it tries to find the K (number) nearest songs taking into consideration genres, artists and popularity, using the KNN supervised machine learning technique
 - One issue with this is that spotify api is not the best, E.g. A LOT of artists do not have any genre associated to them, which, as justified in the next topic, is the main source of genre information used in the algorithm
 - Other issue is that spotify api does not provide, at the time of publish of version 3.1.0, neither song nor album genres, which compromise a portion of the accuracy of the recommendations, still i recommend you give it a try




## Setup

### Requirements:
  - Python installed<br>
 The ideal version, to run the package is 3.8.x, the version in which the package was built over,
 older versions many have some issues, as the package uses a handful of other packages 
 and their versions may conflict
  - Network Connection<br>
 So that a wide range of songs can be analised, it is imperative to have a network connection, at least for the first time executing a script using this package
  - <strong>A fitting playlist</strong><br>
 The perfect use case for this package is that of one big playlist (200+ songs), which you feel like listening to some of them, then others but never, or rarely, all of them, since they belong to diferent genres/styles
  - ## <strong>Patience</strong>
    It may seem funny or a joke, but the first mapping process of the playlist to a local pandas DataFrame... it will take a good while, up to 2.5 to 3 second per song, at 20-40Mbps Internet connection, being in Latam. All these factors play a part in the time for it to first load.
    Just to make it clear, cpu, ram, sdd, etc., will not help much, the issue is to have up to 5 different http requests per song, which make this take so long
    Besides, as of july/2022, Spotify implemented a possible API Response: ["429: Too Many Requests"](https://http.cat/429) which forced this package to implement [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff) in order to complete it's requests, therefore what already took a while, now takes a little bit more, nothing much but still worth noting
  - Jupyter Notebook<br>
 Not exactly a requirement but it is advised that a jupyter notebook is used (even more recommended to use the vscode extension for jupyter notebooks), because it is important, or at least more confortable, to have the variable still in memory and then decide how to use it, without having to run a script multiple times, having to reconnect to Spotify, redownload the playlist, redo some computations, etc.
  - Spotify access<br>
 I mean, you knew that already, right?

  - ### Installing the package<br>
~~~ps1
pip install spotify-recommender-api
~~~


  - ### Importing the package<br>

Firstly, it's necessary to import the method start_api from the package spotify_recommender_api.recommender:
 ~~~ python
 from spotify_recommender_api.recommender import start_api
 ~~~

### Starting the api
  - Gathering the initial information: (playlist_url, user_id)<br>
  
  --- Playlist URL: The playlist url is available when right clicking the playlist name / or going to the three dots that represent the playlist options <br>
  --- Playlist ID: The playlist id is available the hash string between the last '/' in and the '?' in the playlist url<br>
  <img src='./readme-pictures/Playlist Configs.png' width='25%'><br>
  --- User ID: The user id is available when clicking the account, and accessing its information, on spotify's website<br>
  <img src='./readme-pictures/Account.png' width='25%'><br>
  
  - Calling the function:
~~~python
api = start_api(playlist_url='<PLAYLIST_URL>', user_id='<USER_ID>')
~~~
Or
~~~python
api = start_api(playlist_id='<PLAYLIST_ID>', user_id='<USER_ID>')
~~~
Though, to be honest, it is easier and more convenient to use the playlist URL

  - Getting the Auth Token:
  It is a hash token that expires 60 minutes after it is generated, first you need to say that you want to be redirected (y)
  But if it is not the first time you are executing the script in less than an hour, then press(n) and paste the token <br>
  Otherwise press "Get Token", and then select the 5 scope options:<br>
  
  <img src='./readme-pictures/OAuth Scopes.png' width='40%'><br>
  
  Then request it, after that hit crtl+A / command+A to select it all then crtl+C / command+C to copy it.
  Then, back to python, paste it in the field requiring it and press enter.
  Then if you already have a previously generated CSV file format playlist, type csv then hit enter, if you do not have the playlist as previously generated, type web, but know that it will take a good while as said [here](#patience),and if this is the case, go get a cup of coffee, tea, or whatever you are into.
  
  
## Methods
 - get_playlist
~~~python
# Method Use Example
api.get_playlist()
# Function that returns the pandas DataFrame representing the base playlist
~~~ 
 - playlist_to_csv
~~~python
# Method Use Example
api.playlist_to_csv()
# Function that creates a csv format file containing the items in the playlist
# Especially useful when re running the script without having changed the playlist
~~~ 
 - get_medium_term_favorites_playlist
~~~python
# Parameters
get_medium_term_favorites_playlist(with_distance: bool, generate_csv: bool, 
                        generate_parquet: bool, build_playlist: bool)
# Method Use Example
api.get_medium_term_favorites_playlist(generate_csv=True, build_playlist=True)
# Function that returns the pandas DataFrame representing the 
# medium term top 5 recommendation playlist
# All parameters are defaulted to False
# The "distance" is a mathematical value with no explicit units, that is 
# used by te algorithm to find the closest songs
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~ 
 - get_short_term_favorites_playlist
~~~python
# Parameters
get_short_term_favorites_playlist(with_distance: bool, generate_csv: bool, 
                        generate_parquet: bool, build_playlist: bool)
# Method Use Example
api.get_short_term_favorites_playlist(generate_csv=True, build_playlist=True)
# Function that returns the pandas DataFrame representing the 
# short term top 5 recommendation playlist
# All parameters are defaulted to False
# The "distance" is a mathematical value with no explicit units, that is 
# used by te algorithm to find the closest songs
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~ 
 - get_recommendations_for_song
~~~python
# Parameters
get_recommendations_for_song(song: str, K: int, with_distance: bool, generate_csv: bool, 
                        generate_parquet: bool, build_playlist: bool, print_base_caracteristics: bool)
# Method Use Example
api.get_recommendations_for_song(song='<SONG_NAME>', K=50)
# Function that returns the pandas DataFrame representing the 
# given song recommendation playlist
# the 'song' and 'K' parameters are mandatory and the rest is
# defaulted to False
# The "distance" is a mathematical value with no explicit units, that is 
# used by te algorithm to find the closest songs
# print_base_caracteristics will display the parameter song information
# Note that it can be used to update a playlist if the given song already
# has its playlist generated by this package
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~ 
 - get_most_listened
~~~python
# Parameters
get_most_listened(time_range: str = 'long', K: int = 50, build_playlist: bool = False)
# Method Use Example
api.get_most_listened(time_range='short', K=53)
# Function that returns the pandas DataFrame representing the 
# given time range most listened tracks playlist
# No parameters are mandatory but the default values should be noted 
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~ 
 - update_all_generated_playlists
### WILL CHANGE THE USER'S LIBRARY DRASTICALLY
~~~python
# Parameters
update_all_generated_playlists(K: int = 50)
# Method Use Example
api.update_all_generated_playlists()
# Function updates all the playlists once generated by this package in batch 
# Note that if only a few updates are preferred, the methods above are a better fit
# No parameters are mandatory but the default values should be noted 
~~~ 
 - get_playlist_trending_genres
~~~python
# Parameters
get_playlist_trending_genres(time_range: str = 'all_time', plot_top: int|bool = False)
# Method Use Example
api.get_playlist_trending_genres()
# Function that returns a pandas DataFrame with all genres within the playlist and both their 
# overall appearance and the percentage of their appearance over the entire playlist
# in the given time_range
# Setting the plot_top parameter to one of the following [5, 10, 15] will plot a barplot
# with this number of the most listened genres in the playlist
~~~ 
 - get_playlist_trending_artists
~~~python
# Parameters
get_playlist_trending_artists(time_range: str = 'all_time', plot_top: int|bool = False)
# Method Use Example
api.get_playlist_trending_artists()
# Function that returns a pandas DataFrame with all artists within the playlist and both their
# overall appearance and the percentage of their appearance over the entire playlist
# in the given time_range
# Setting the plot_top parameter to one of the following [5, 10, 15] will plot a barplot
# with this number of the most listened artists in the playlist
~~~
 - artist_specific_playlist
~~~python
# Parameters
artist_specific_playlist(artist_name: str, K: int = 50, complete_with_similar: bool = False, build_playlist: bool = False, print_base_caracteristics: bool = False)
# Method Use Example
api.artist_specific_playlist(artist_name='Joyner Lucas', K=50, complete_with_similar=True, print_base_caracteristics=True, build_playlist=True)
# Function that returns a pandas DataFrame with all songs from a specific artist within the playlist 
# and can complete that new playlist with the closest songs to that artist, and create it in the users account
# complete_with_similar is a Flag that indicates if the playlist will be completed with the closet songs related to the artist or only their songs
# print_base_caracteristics will display the parameter song information
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~

# OG Scripts
###DEPRECATED###
### Context
This script, in jupyter notebook format for organization purposes, applies the technique called K Nearest Neighbors to find the 50 closest songs to either one chosen or one of the users top 5(short term), all within a specific Spotify playlist, in order to maintain the most consistency in terms of the specific chosen style, and creates a new playlist with those songs in the user's library, using their genres, artists and overall popularity as metrics to determine indexes of comparison between songs

### Variations
There are also 2 variations from that, which consist of medium term favorites related top 100 and "short term top 5" related top 50 songs. They vary from OG model since the base song(s) is(are) not chosen by hand but statistically

### DISCLAIMER ###
Not fit for direct use since some information such as client id, client secret, both of which are, now, in a hidden script on .gitignore so that it is not made public, have to be informed in order for the Spotify Web API to work properly.
And also, these scripts are deprecated, so they will not have any maintenance or overtime improvements / new features





## Packages used
 - Pandas 
~~~ps1
pip install pandas
~~~
 - Requests
~~~ps1
pip install requests
~~~
 - Seaborn
~~~ps1
pip install seaborn
~~~
 - Re (re)
 - Os (os)
 - Json (json)
 - Time (time)
 - Datetime (datetime)
 - Dateutil (dateutil)
 - Operator (operator)
 - Functools (functools)
 - Webbrowser (webbrowser)
 

# Contributing
Well, since this is a really simple package, contributing is always welcome, just as much as creating issues experienced with the package

In order to better organize this contributions, it would be ideal that all PRs follow the template:

## PR Template
 WHAT: <br>
 A brief description of the improvements
 
 WHY: <br>
A explanation on why those changes were needed, necessary, or at least, why is was on the best interest of the package users

CHANGES: <br>
List of changes made, can be the name of the commits made, or a simple changes list

## Commits
Ideally the commits should make use of the convention of [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) <br>
Something i recommend is the usage of either the [Commitizen](https://github.com/commitizen/cz-cli) terminal extension or the [Commit Message Editor](https://marketplace.visualstudio.com/items?itemName=adam-bender.commit-message-editor) VSCode Extension
