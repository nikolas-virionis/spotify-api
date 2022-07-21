import time
import json
import datetime
import pandas as pd
import spotify_recommender_api.requests as requests
from dateutil import tz


def playlist_url_to_id(url: str) -> str:
    """Extracts the playlist id from it's URL

    Args:
        url (str): The playlist public url

    Returns:
        str: The Spotify playlist Id
    """
    uri = url.split('?')[0]
    id = uri.split('open.spotify.com/playlist/')[1]
    return id


def get_total_song_count(playlist_id: str, headers: dict) -> int:
    """Function returns the total number of songs in the playlist

    Args:
        playlist_id (str): The Spotify playlist Id
        headers (dict): The request headers, containing the auth information

    Returns:
        int: The total number of songs in the playlist
    """
    playlist_res = requests.get_request(
        url=f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers)

    return playlist_res.json()["tracks"]["total"]


def add_items_to_list(item_list: 'list[str]', items: 'list[str]') -> 'list[str]':
    """Function represents a way to have only unique values for a given list while constantly appending new genre values

    Args:
        item_list (list[str]): the overall, big, complete, list of items
        items (list[str]): the possibly new item values

    Returns:
        list[str]: the new, and deduplicated, complete list of items
    """
    for item in items:
        if item not in item_list:
            item_list.append(item)

    return item_list


def song_data(song: dict) -> 'tuple[str, str, float, list[str], datetime.datetime]':
    """Function that gets additional information about the song, like its name, artists, id, popularity, date when it was added to the playlist, etc.

    Args:
        song (dict): The song dictionary fetched from the Spotify API

    Returns:
        tuple[str, str, float, list[str], datetime.datetime]: A tuple containing the song's information
    """"""
    Function that gets additional information about the song
    like its name, artists, id, popularity

    # Parameters
    - song: the song raw dictionary
    """
    return song["track"]['id'], song["track"]['name'], song["track"]['popularity'], [artist["name"] for artist in song["track"]["artists"]], song['added_at']


def item_list_indexed(items: 'list[str]', all_items: 'list[str]') -> 'list[int]':
    """Function that returns the list of items, mapped to the overall list of items, in a binary format
    Useful for the overall execution of the algorithm which determines the distance between each song

    Args:
        items (list[str]): list of items for a given song
        all_items (list[str]): all the items inside the entire playlist

    Returns:
        list[int]: indexed list of items in binary format in comparison to all the items inside the playlist
    """
    indexed = []
    for all_genres_x in all_items:

        continue_outer = False
        for item in items:
            index = all_genres_x == item
            if index:
                continue_outer = True
                indexed.append(int(True))
                break

        if continue_outer:
            continue

        indexed.append(int(False))

    return indexed


def playlist_exists(name: str, base_playlist_name: str, headers: dict, _update_created_playlists: bool = False) -> 'str|bool':
    """Function used to check if a playlist exists inside the user's library
    Used before the creation of a new playlist

    Args:
        name (str): name of the playlist being created, which could easily be bypassed, if the playlist names were not made automatically
        base_playlist_name (str): name of the base playlist
        headers (dict): Request headers

    Returns:
        str|bool: If the playlist already exists, returns the id of the playlist, otherwise returns False
    """
    total_playlist_count = requests.get_request(
        url=f'https://api.spotify.com/v1/me/playlists?limit=1', headers=headers).json()['total']
    playlists = []
    for offset in range(0, total_playlist_count, 50):
        request = requests.get_request(
            url=f'https://api.spotify.com/v1/me/playlists?limit=50&{offset=!s}',  headers=headers).json()

        playlists += list(map(lambda playlist: (
            playlist['id'], playlist['name'], playlist['description']), request['items']))

    for playlist in playlists:

        if playlist[1] == name and (f', within the playlist {base_playlist_name}' in playlist[2] or _update_created_playlists):
            return playlist[0]

    return False


def query_audio_features(song: pd.Series, headers: dict) -> 'list[float]':
    """Queries the audio features for a given song and returns the ones that match the recommendations within this package

    Args:
        song (pd.Series): song containing its base information
        headers (dict): Request headers

    Returns:
        list[float]: list with the audio features for the given song
    """

    id = song['id']

    audio_features = requests.get_request(
        url=f'https://api.spotify.com/v1/audio-features/{id}',
        headers=headers
    ).json()

    return [audio_features['danceability'], audio_features['energy'], audio_features['instrumentalness'], audio_features['tempo'], audio_features['valence']]


def get_datetime_by_time_range(time_range: str = 'all_time') -> datetime.datetime:
    """Calculates the datetime that corresponds to the given time range before the current date

    Args:
        time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.

    Raises:
        ValueError: If the time_range parameter is not valid the error is raised.

    Returns:
        datetime.datetime: Datetime of the specified time_range before the current date
    """
    if time_range not in ['all_time', 'month', 'trimester', 'semester', 'year']:
        raise ValueError(
            'time_range must be one of the following: "all_time", "month", "trimester", "semester", "year"')

    now = datetime.datetime.now(tz=tz.gettz('UTC'))
    date_options = {
        'all_time': datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=tz.gettz('UTC')),
        'month': now - datetime.timedelta(days=30),
        'trimester': now - datetime.timedelta(days=90),
        'semester': now - datetime.timedelta(days=180),
        'year': now - datetime.timedelta(days=365),
    }

    return date_options[time_range]


def list_to_count_dict(dictionary: dict, item: str) -> dict:
    """Tranforms a list of strings into a dictionary which has the strings as keys and the amount they appear as values

    Note:
        This function needs to be used in conjunction with a reduce function

    Args:
        dictionary (dict): Dictionary to be created / updated
        item (str): new item from the list

    Returns:
        dict: dictionary with the incremented value that represents the 'item' key
    """

    if item in dictionary.keys():
        dictionary[item] += 1
    else:
        dictionary[item] = 1

    return dictionary


def value_dict_to_value_and_percentage_dict(dictionary: 'dict[str, int]') -> 'dict[str, dict[str, float]]':
    """Transforms a dictionary containing only values for a given key into a dictionary containing the values and the total percentage of that key

    Args:
        dictionary (dict): dictionary with only the values for each

    Returns:
        dict[str, dict[str, float]]: new dictionary with values and total percentages
    """
    dictionary = {key: {'value': value, 'percentage': round(value / dictionary['total'], 5)} for key, value in dictionary.items()}

    return dictionary

def print_base_caracteristics(*args):
    name, genres, artists, popularity, danceability, energy, instrumentalness, tempo, valence = args

    print(f'{name = }')
    print(f'{artists = }')
    print(f'{genres = }')
    print(f'{popularity = }')
    print(f'{danceability = }')
    print(f'{energy = }')
    print(f'{instrumentalness = }')
    print(f'{tempo = }')
    print(f'{valence = }')

def get_base_playlist_name(playlist_id: str, headers: dict) -> str:
    """Returns the base playlist name given the playlist id

    Args:
        playlist_id (str): The Spotify playlist id
        headers (dict): Request headers

    Returns:
        str: The base playlist name
    """

    playlist = requests.get_request(
        url=f'https://api.spotify.com/v1/playlists/{playlist_id}',
        headers=headers
    ).json()

    playlist_name = playlist['name']

    return playlist_name
