import logging
import warnings
import datetime
import functools

from dateutil import tz
from typing import Any, Callable
from spotify_recommender_api.requests.api_handler import PlaylistHandler


def playlist_url_to_id(url: str) -> str:
    """Extracts the playlist id from it's URL

    Args:
        url (str): The playlist public url

    Returns:
        str: The Spotify playlist Id
    """
    uri = url.split('?')[0]

    return uri.split('open.spotify.com/playlist/')[1]

def item_list_indexed(items: 'list[str]', all_items: 'list[str]') -> 'list[str]':
    """Function that returns the list of items, mapped to the overall list of items, in a binary format
    Useful for the overall execution of the algorithm which determines the distance between each song

    Args:
        items (list[str]): list of items for a given song
        all_items (list[str]): all the items inside the entire playlist

    Returns:
        list[int]: indexed list of items in binary format in comparison to all the items inside the playlist
    """

    return [str(int(all_genres_x in items)) for all_genres_x in all_items]

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
        raise ValueError('time_range must be one of the following: "all_time", "month", "trimester", "semester", "year"')

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

    dictionary[item] = dictionary.get(item, 0) + 1

    return dictionary


def value_dict_to_value_and_percentage_dict(dictionary: 'dict[str, int]') -> 'dict[str, dict[str, float]]':
    """Transforms a dictionary containing only values for a given key into a dictionary containing the values and the total percentage of that key

    Args:
        dictionary (dict): dictionary with only the values for each

    Returns:
        dict[str, dict[str, float]]: new dictionary with values and total percentages
    """
    return {
        key: {
            'value': value,
            'percentage': round(value / dictionary['total'], 5)
        }
        for key, value in dictionary.items()
    }

def print_base_caracteristics(*args):
    """
    Function that receives a list of values and print them

    Args:
        name (str): name of the song
        artists (list[str]): song's artists
        genres (list[str]): song's genres
        popularity (int): song's popularity
        danceability (float): song's danceability
        loudness (float): song's loudness
        energy (float): song's energy
        instrumentalness (float): song's instrumentalness
        tempo (float): song's tempo
        valence (float): song's valence

    """
    id, name, genres, artists, popularity, danceability, loudness, energy, instrumentalness, tempo, valence = args

    logging.info(f'{id = }')
    logging.info(f'{name = }')
    logging.info(f'{artists = }')
    logging.info(f'{genres = }')
    logging.info(f'{popularity = }')
    logging.info(f'{danceability = }')
    logging.info(f'{loudness = }')
    logging.info(f'{energy = }')
    logging.info(f'{instrumentalness = }')
    logging.info(f'{tempo = }')
    logging.info(f'{valence = }')


def get_base_playlist_name(playlist_id: str) -> str:
    """Returns the base playlist name given the playlist id

    Args:
        playlist_id (str): The Spotify playlist id

    Returns:
        str: The base playlist name
    """

    playlist = PlaylistHandler.playlist_details(playlist_id)

    return playlist.json()['name']


def deprecated(func: Callable[..., Any]) -> Callable[..., Any]:
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs) -> Any:
        warnings.simplefilter('always', DeprecationWarning)  # turn off filter
        warnings.warn(f"Call to deprecated function {func.__name__}.", category=DeprecationWarning, stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning)  # reset filter
        return func(*args, **kwargs)
    return new_func
