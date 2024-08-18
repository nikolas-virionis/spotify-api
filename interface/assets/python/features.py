import time
import json

from pyscript import window, document
from spotify_recommender_api.web import start_api_for_web

# print('Starting API for web...')
# window.localStorage.removeItem('spotify-recommender-token')
# window.open(
#     'https://accounts.spotify.com/authorize?client_id=ddf4e1944b254754ba1a17d0dd8e517b&response_type=code&redirect_uri=http://127.0.0.1:5500/spotify-api/interface/authorization.html&scope=playlist-modify-private playlist-read-private user-library-read user-library-modify user-top-read user-read-recently-played',
#     '_blank',
#     'location=yes,height=570,width=520,scrollbars=yes,status=yes'
# )

# time.sleep(1)
# for i in range(300):
#     time.sleep(1)
# else:
#     window.alert('Timeout while waiting for the token')
#     window.location.href = '/'

setup_info = json.loads(window.localStorage.getItem('spotify-recommender-setup'))

if not setup_info:
    window.alert('No setup info found in local storage. Please return to home and press start to setup application.')
    window.location.href = '/'

if not (setup_info.get('liked_songs') or setup_info.get('playlist_id') or setup_info.get('playlist_url')):
    document.querySelector('#container-playlist').style.display = 'none'

api = start_api_for_web(**setup_info, log_level='DEBUG')

def get_most_listened(event):
    time_range = document.querySelector('#time-range-most-listened').value
    build_playlist = document.querySelector('#checkbox-most-listened').checked
    number_of_songs = int(document.querySelector('#number-of-songs-most-listened').value)

    result = api.get_most_listened(
        time_range=time_range,
        build_playlist=build_playlist,
        number_of_songs=number_of_songs
    )

    window.alert('Most listened songs playlist created successfully')

def get_recently_played(event):
    time_range = document.querySelector('#time-range-recently-played').value
    build_playlist = document.querySelector('#checkbox-recently-played').checked
    number_of_songs = int(document.querySelector('#number-of-songs-recently-played').value)

    result = api.get_recently_played(
        time_range=time_range,
        build_playlist=build_playlist,
        number_of_songs=number_of_songs
    )

    window.alert('Recently Played songs playlist created successfully')

def get_recently_played_recommendations(event):
    time_range = document.querySelector('#time-range-recently-played-recommendations').value
    main_criteria = document.querySelector('#main-criteria-recently-played-recommendations').value
    build_playlist = document.querySelector('#checkbox-recently-played-recommendations').checked
    number_of_songs = int(document.querySelector('#number-of-songs-recently-played-recommendations').value)

    result = api.get_recently_played_recommendations(
        time_range=time_range,
        main_criteria=main_criteria,
        build_playlist=build_playlist,
        number_of_songs=number_of_songs,
    )

    window.alert('Recently Played based recommendation playlist created successfully')

def get_profile_recommendation(event):
    time_range = document.querySelector('#time-range-profile-recommendation').value
    main_criteria = document.querySelector('#main-criteria-profile-recommendation').value
    build_playlist = document.querySelector('#checkbox-profile-recommendation').checked
    number_of_songs = int(document.querySelector('#number-of-songs-profile-recommendation').value)

    result = api.get_profile_recommendation(
        time_range=time_range,
        main_criteria=main_criteria,
        build_playlist=build_playlist,
        number_of_songs=number_of_songs,
    )

    window.alert('Profile based recommendation playlist created successfully')

def get_general_recommendation(event):
    time_range = document.querySelector('#time-range-most-listened').value
    build_playlist = document.querySelector('#checkbox-most-listened').checked
    number_of_songs = int(document.querySelector('#number-of-songs-most-listened').value)

    result = api.get_general_recommendation(
        time_range=time_range,
        build_playlist=build_playlist,
        number_of_songs=number_of_songs
    )

    window.alert('Most listened songs retrieved successfully')