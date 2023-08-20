# spotify-recommender
![GitHub repo size](https://img.shields.io/github/repo-size/nikolas-virionis/spotify-api)
![GitHub last commit](https://img.shields.io/github/last-commit/nikolas-virionis/spotify-api?style=plastic)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/spotify-recommender-api?style=plastic)
![PyPI](https://img.shields.io/pypi/v/spotify-recommender-api?style=plastic)
![PyPI - Downloads](https://img.shields.io/pypi/dm/spotify-recommender-api?style=plastic)<br>

<img src='./readme-pictures/Spotify Logo.png' width='60%'>

- [spotify-recommender](#spotify-recommender)
  - [Use Case](#use-case)
  - [Setup](#setup)
    - [Requirements:](#requirements)
    - [Starting the api](#starting-the-api)
  - [Methods](#methods)
  - [Suggestions](#suggestions)
- [OG Scripts](#og-scripts)
    - [Context](#context)
    - [Variations](#variations)
    - [DISCLAIMER](#disclaimer)
- [Packages used](#packages-used)
- [Contributing](#contributing)
  - [PR Template](#pr-template)
  - [Commits](#commits)


## Use Case
 - This is the first section of this readme, because, you will see, that this package can help, but nothing is perfect, so it will, as long as you fit in the use cases ;(
 - There are more general recommendation features, such as profile, playlist and general recommendations, but also there are a few other features which would have the perfect use case as the one that has one playlist (or more) where you put a lot of songs in different times and mood styles, and when you listen to it, you feel like only listening to a part of it, some days later, that part is useless, but some other part is awesome. The big issue here is that those "parts" are shuffled, all across the playlist. Then how would one find those songs they crave, today, tomorrow, and later? Speaking from experience, it is not worth it to map manually a 1000-song playlist and filter out 50 or 100 of them.
 - This package comes to solve this issue, roughly, because it tries to find the nearest songs taking into consideration genres, artists, popularity, and some audio features, such as danceability, energy, instrumentalness, tempo, and valence, using an adaptation of the KNN supervised machine learning technique to find the closest songs to some threshold.
 - One issue with this is that Spotify API is not perfect, E.g. a lot of artists do not have any genre associated with them, which, as justified in the next topic, is the main source of genre information used
 - Another issue is that Spotify API does not provide, at the time of publication of version 5.0.0, neither song nor album genres, which compromises a portion of the accuracy of the recommendations. Still, I recommend you give it a try since because of the use of all other variables, it has a decent to good accuracy.



## Setup

### Requirements:
  - Python installed<br>
 The ideal version, to run the package is 3.8.x, the version on top of which the package was built, newer version should be fine and older versions may have some issues, as the package uses a handful of other packages, and python features, and their versions may conflict.
  - Network Connection<br>
 So that a wide range of songs can be analyzed, it is imperative to have a network connection, at least for the first time executing a script using this package.
  - A fitting playlist<br>
 For the playlist related features, the perfect use case for this package is that of one big playlist (200+ songs), which you feel like listening to some of them, then others, but never, or rarely, all of them, since they belong to different genres/styles.
  - ## <strong>Patience</strong>
    It may seem funny or a joke, but if one wants to use any playlist related features, the first mapping process of the playlist to a local pandas DataFrame... it will take a good while, up to 2.5 to 3 seconds per song, at 20-40Mbps Internet connection, being in Latam. All these factors play a part in the time for it to the first load.
    Just to make it clear, CPU, ram, sdd, etc., will not help much, the issue is to have up to 7 different HTTP requests per song, to retrieve all information needed, which makes this take so long.
    Besides, as of July/2022, Spotify implemented a possible API Response: ["429: Too Many Requests"](https://http.cat/429) which forced this package to implement [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff) to complete its requests, therefore what already took a while, now takes a little bit more
  - Jupyter Notebook<br>
 Not exactly a requirement but it is advised that a Jupyter notebook is used (even more recommended to use the vscode extension for Jupyter notebooks) because it is important, or at least more comfortable, to have the variable still in memory and then decide how to use it, without having to run and rerun a script multiple times, having to reconnect to Spotify, redownload the playlist, redo some computations, etc.
  - Spotify access<br>
 I mean, you knew that already, right?

  - ### Installing the package<br>
~~~ps1
pip install spotify-recommender-api
~~~


  - ### Importing the package<br>

Firstly, it's necessary to import the method start_api from the package spotify_recommender_api:
 ~~~ python
 from spotify_recommender_api import start_api
 ~~~

### Starting the api
  - Gathering the initial information: (playlist_url, user_id)<br>
  - The only mandatory parameter is user_id. If the user wants to use the playlist related features, they need to provide a playlist either on the start_api function or the api.select_playlist method.

  --- Playlist URL: The playlist URL is available when right-clicking the playlist name / or going to the three dots that represent the playlist options <br>
  --- Playlist ID: The playlist id is available as the hash string between the last '/' in and the '?' in the playlist url<br>
  <img src='./readme-pictures/Playlist Configs.png' width='25%'><br>
  --- User ID: The user id is available when clicking the account, and accessing its information, on Spotify's website<br>
  <img src='./readme-pictures/Account.png' width='25%'><br>
  --- Liked Songs: A flag to pass in case the playlist you want to use is your profile Liked Songs <br>
  --- Log level: the logging package log level. Defaults to INFO, but can be DEBUG, INFO, WARNING and ERROR <br>
  --- Retrieval Type: The retrieval_type parameter must be either "csv" or "web"

  - Calling the function:
~~~python
api = start_api(user_id='<USER_ID>')
~~~
Or
~~~python
api = start_api(user_id='<USER_ID>', playlist_url='<PLAYLIST_URL>', retrieval_type='csv')
~~~
Or
~~~python
api = start_api(user_id='<USER_ID>', playlist_id='<PLAYLIST_ID>', retrieval_type='web')
~~~
Or
~~~python
api = start_api(user_id='<USER_ID>', liked_songs=True, retrieval_type='web')
~~~
Though, to be honest, it is easier and more convenient to use either the playlist URL or the liked_songs flag

  - Getting the Auth Token:
  It is a hash token that expires 60 minutes after it is generated, and after April 22nd, 2023 it has been fully refactored, due to a change in the Spotify API Authentication methods, which invalidated the previous way.
  Now As soon as you call the start_api to function a fast API server will be launched in port 8000.<br>
  Also there will be a web browser opened so that the user can click on the button Authorize, log in with their Spotify account, and then, the authentication is completed for that usage of the package.
  After version 5.0.0 (July 15th, 2023), within this 60 minute period, the Access token will be "cached" locally for faster access, and after this 60 minute period, there are two things that can happen. If no function was running, nothing will happen, and the next time any function is called, it will be necessary to login again. Or if there is a function running, the access token expired error will be caught, and automatically the fast API server will be launched again, so that the user can reauthenticate, and automatically after the authentication the function which was running will continue from where it left off.


## Methods
 - select_playlist
~~~python
# Parameters
select_playlist(
    playlist_id: str = None,
    playlist_url: str = None,
    liked_songs: bool = False,
    retrieval_type: str = None
)
# Method Use Example
api.select_playlist(liked_songs=True, retrieval_type='web')
# Function to select a playlist to be mapped and be available on all the playlist-related recommendation
# functions on an already existing authentication context
# The retrieval_type parameter must be either "csv" or "web"
~~~~~~
 - get_most_listened
~~~python
# Parameters
get_most_listened(
    number_of_songs: int = 50,
    build_playlist: bool = False,
    time_range: str = 'long_term',
)
# Method Use Example
api.get_most_listened(time_range='short_term', number_of_songs=50)
# Function that returns the pandas DataFrame representing the
# given the time range most listened to tracks playlist
# No parameters are mandatory but the default values should be noted
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~
 - get_profile_recommendation
~~~python
# Parameters
get_profile_recommendation(
    number_of_songs: int = 50,
    main_criteria: str = 'mixed',
    save_with_date: bool = False,
    build_playlist: bool = False,
    time_range: str = 'short_term'
)
# Method Use Example
api.get_profile_recommendation(number_of_songs=50, main_criteria='tracks')
# Function that returns a pandas DataFrame with profile-based recommendations, and creates it in the user account
# main_criteria is the base info to get the recommendations
# save_with_date is a flag to save the recommendations as a playlist at a point in time Snapshot
# time_range refers to the range from the profile information that will be used to get the recommendation
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~
 - get_general_recommendation
~~~python
# Parameters
get_general_recommendation(
    number_of_songs: int = 50,
    genres_info: list[str] = [],
    artists_info: list[str] = [],
    build_playlist: bool = False,
    use_main_playlist_audio_features: bool = False,
    tracks_info: list[str] | list[tuple[str, str]] | list[list[str]] | dict[str, str] = [],
)
# Method Use Example
api.get_general_recommendation(
    build_playlist=True,
    genres_info=['rap'],
    artists_info=['NF', 'Logic'],
    tracks_info={'Clouds': 'NF'},
)
# Function that returns a pandas DataFrame with artists, genres, and/or tracks-based recommendations, and creates it in the user account
# genres_info, artists_info, and tracks_info are the lists of information that the recommendation would be based on, and the sim of their lengths must not surpass 5.
# use_main_playlist_audio_features is the flag to indicate if the playlist-provided audio features will be used as the target for a better recommendation, BUT IT ONLY IS ALLOWED WHEN THE USER PASSED A PLAYLIST, OTHERWISE IT WILL RAISE AN ERROR.
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~~~~
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
# Function that creates a CSV format file containing the items in the playlist
# Especially useful when re-running the script without having changed the playlist
~~~
 - get_recommendations_for_song
~~~python
# Parameters
get_recommendations_for_song(
    song_name: str,
    artist_name: str,
    with_distance: bool,
    build_playlist: bool,
    number_of_songs: int,
    print_base_caracteristics: bool
)
# Method Use Example
api.get_recommendations_for_song(
    number_of_songs=50,
    song_name='<SONG_NAME>',
    artist_name='<ARTIST_NAME>'
)
# Function that returns the pandas DataFrame representing the
# given song recommendation playlist
# The 'song_name', 'artist_name' and 'number_of_songs' parameters are mandatory and the rest is
# defaulted to False
# The "distance" is a mathematical value with no explicit units, that is
# used by the algorithm to find the closest songs
# print_base_caracteristics will display the parameter song information
# Note that it can be used to update a playlist if the given song already
# has its playlist generated by this package
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
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
# Setting the plot_top parameter to any integer less tha or equal to 30 will plot a barplot with that many top genres
# With this number of the most listened genres in the playlist
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
# Setting the plot_top parameter to any integer less tha or equal to 30 will plot a barplot with that many top artists
# With this number of the most listened artists in the playlist
~~~
 - artist_only_playlist
~~~python
# Parameters
artist_only_playlist(
    artist_name: str,
    number_of_songs: int = 50,
    build_playlist: bool = False,
    ensure_all_artist_songs: bool = True
)
# Method Use Example
api.artist_only_playlist(
    number_of_songs=50,
    build_playlist=True,
    artist_name='Joyner Lucas',
)
# Function that returns a pandas DataFrame with all songs from a specific artist within the playlist and create it in the user account
# The ensure_all_artist_songs Flag serves the purpose of making sure all the artist's songs are present in a "This is" type playlist, regardless of the number_of_songs.
# This behavior is turned off by setting the Flag as False
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~
 - artist_specific_playlist
~~~python
# Parameters
artist_specific_playlist(
    artist_name: str,
    number_of_songs: int = 50,
    with_distance: bool = False,
    build_playlist: bool = False,
    print_base_caracteristics: bool = False,
)
# Method Use Example
api.artist_specific_playlist(
    number_of_songs=50,
    build_playlist=True,
    artist_name='Joyner Lucas',
    print_base_caracteristics=True,
)
# Function that returns a pandas DataFrame with all songs from a specific artist within the playlist and complete that new playlist with the closest songs to that artist, and create it in the user account
# print_base_caracteristics will display the parameter song information
# The "distance" is a mathematical value with no explicit units, that is
# used by the algorithm to find the closest songs
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~
 - audio_features_extraordinary_songs
~~~python
# Parameters
audio_features_extraordinary_songs()
# Method Use Example
api.audio_features_extraordinary_songs()
# Function that returns a dictionary containing the songs that have the maximum and minimum values
# for the 5 audio features used in this package: ['danceability', 'energy', 'instrumentalness', 'tempo', 'valence']
~~~
 - audio_features_statistics
~~~python
# Parameters
audio_features_statistics()
# Method Use Example
api.audio_features_statistics()
# Function that returns the statistics (max, min and mean) for the audio features within the playlist.
# The 5 audio features used in this package: ['danceability', 'energy', 'instrumentalness', 'tempo', 'valence']
~~~
 - get_playlist_recommendation
~~~python
# Parameters
get_playlist_recommendation(
    number_of_songs: int = 50,
    time_range: str = 'all_time',
    main_criteria: str = 'mixed',
    save_with_date: bool = False,
    build_playlist: bool = False,
)
# Method Use Example
api.get_playlist_recommendation(build_playlist=True)
# Function that returns a pandas DataFrame with playlist-based recommendations, and creates it in the user account
# main_criteria is the base info to get the recommendations
# time_range is the time range to be looked at for the recommendations baseline
# save_with_date is a flag to save the recommendations as a playlist as a point in time Snapshot
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~
 - get_songs_by_mood
~~~python
# Parameters
get_songs_by_mood(
    mood: str,
    number_of_songs: int = 50,
    build_playlist: bool = False,
    exclude_mostly_instrumental: bool = False
)
# Method Use Example
api.get_songs_by_mood(mood='happy', build_playlist=True)
# Function to create a playlist based on the general mood of its songs
# exclude_mostly_instrumental is a flag to remove the songs that are more than 80% instrumental from the song base
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~~~~
 - playlist_songs_based_on_most_listened_tracks
~~~python
# Parameters
playlist_songs_based_on_most_listened_tracks(
    number_of_songs: int = 50,
    build_playlist: bool = False,
    time_range: str = 'short_term',
)
# Method Use Example
api.playlist_songs_based_on_most_listened_tracks(
    number_of_songs=50,
    build_playlist=True,
    time_range='medium_term',
)
# Function to create a playlist with songs from the base playlist that are the closest to the user's most listened songs
# BUILD_PLAYLIST WILL CHANGE THE USER'S LIBRARY IF SET TO TRUE
~~~~~~
 - update_all_generated_playlists
~~~python
# Parameters
update_all_generated_playlists(
    playlist_types_to_update: list[str] = ['most-listened-tracks', 'song-related', 'artist-mix', 'artist-full', 'playlist-recommendation', 'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation', 'mood', 'most-listened-recommendation'],
    playlist_types_not_to_update: list[str] = []
)
# Method Use Example
api.update_all_generated_playlists()
# or for example api.update_all_generated_playlists(playlist_types_to_update=['playlist-recommendation'])
# Function updates all the playlists once generated by this package in batch
# Note that if only a few updates are preferred, the methods above are a better fit\
# But for any combination of types of updates this method fits well
~~~

## Suggestions
 - ### Advice towards leaving everything more organized <br>
   It is recommended that the user creates folders to group the playlists created by this package, because after creating more than 150 playlists, your library can, and probably will, become a mess. Unfortunately, the Spotify API does not allow users to create or manipulate folders in the same way that a file system would work. The only way to create folders is manually, through the web page or app. Some suggestions for folders that could be useful include "Song Related" for playlists created using the get_recommendations_for_song function, "Profile Recommendations" for playlists created with get_profile_recommendation, "Personal Trends" for playlists created with get_most_listened, and any other categories that the user thinks would be useful.
 - ### Spotify Enhance Feature vs spotify-recommender-api package <br>
    I think it is really possible, and legitimate, to wonder if the Enhance Feature (on mobile called Smart Shuffle) replaces the use of this package. However, in my opinion, they can actually be used in a complementary fashion. For example, you can create a profile recommendation based on your most listened tracks, and then use the Enhance feature to increase the number of new and enjoyable songs in that playlist, both from the profile recommendation playlist and from the enhancement itself. This can improve the overall listening experience. It's worth noting that while the Enhance Feature was introduced after the development of most of the package, they do not conflict with each other.


# OG Scripts
###DEPRECATED### and not maintained since 2022
### Context
This script, in jupyter notebook format for organization purposes, applies the technique called K Nearest Neighbors to find the 50 closest songs to either one chosen or one of the users top 5(short term), all within a specific Spotify playlist, in order to maintain the most consistency in terms of the specific chosen style, and creates a new playlist with those songs in the user's library, using their genres, artists and overall popularity as metrics to determine indexes of comparison between songs

### Variations
There are also 2 variations from that, which consist of medium term favorites related top 100 and "short term top 5" related top 50 songs. They vary from OG model since the base song(s) is(are) not chosen by hand but statistically

### DISCLAIMER ###
Not fit for direct use since some information such as client id, client secret, both of which are, now, in a hidden script on .gitignore so that it is not made public, have to be informed in order for the Spotify Web API to work properly.
And also, as of January 2022, these scripts are deprecated, so they will not have any maintenance or overtime improvements or new features



# Packages used
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
 - Matplotlib
~~~ps1
pip install matplotlib
~~~
 - FastAPI
~~~ps1
pip install fastapi
~~~
 - Uvicorn
~~~ps1
pip install uvicorn
~~~
 - Re (re)
 - Os (os)
 - Abc (abc)
 - Json (json)
 - Time (time)
 - Pytz (pytz)
 - Typing (typing)
 - Logging (logging)
 - Datetime (datetime)
 - Dateutil (dateutil)
 - Traceback (traceback)
 - Threading (threading)
 - Functools (functools)
 - Contextlib (contextlib)
 - Webbrowser (webbrowser)
 - Dataclasses (dataclasses)


# Contributing
Well, since this is a really simple package, contributing is always welcome, just as much as creating issues experienced with the package

In order to better organize these contributions, it would be ideal that all PRs follow the template:

## PR Template
 WHAT: <br>
 A brief description of the improvements

 WHY: <br>
A explanation on why those changes were needed, necessary, or at least, why it was on the best interest of the package users, for the package to have this changed

CHANGES: <br>
List of changes made, can be the list of the commits made, or a simple changes list

## Commits
Ideally the commits should make use of the convention of [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) <br>
Something I recommend is the usage of either the [Commitizen](https://github.com/commitizen/cz-cli) terminal extension or the [Commit Message Editor](https://marketplace.visualstudio.com/items?itemName=adam-bender.commit-message-editor) VSCode Extension
