import time
import json
import datetime
from requests import get, post, delete, put


def exponential_backoff(func, retries: int = 5):
    """Exponential backoff strategy (https://en.wikipedia.org/wiki/Exponential_backoff)
    in order to retry certain function after exponetially increasing delay, to overcome "429: Too Many Requests" error

    Args:
        func (function): function to be executed with exponential backoff
        retries (int, optional): Number of maximum retries before raising an exception. Defaults to 5.

    Raises:
        Exception: Error raised in the function after {retries} attempts

    Returns:
        Any: specified function return
    """
    x = 0
    while x <= retries:
        try:
            response = func()
            if 'error' in response.json():
                raise Exception(f"{response.json()['error']['status']}: {response.json()['error']['message']}")
            return response
        except Exception as e:
            if any([errorCode in str(e) for errorCode in ['404', '50']]):
                continue
            if '429' not in str(e):
                raise Exception(e)
            if x == 0:
                print('\nExponential backoff triggered: ')
            x += 1
            if x >= retries:
                print(
                    f'AFTER {retries} ATTEMPTS, THE EXECUTION OF THE FUNCTION FAILED WITH THE EXCEPTION: {e}')
                raise Exception(e)
            else:
                sleep = 2 ** x
                print(f'\tError raised: sleeping {sleep} seconds')
                time.sleep(sleep)


def get_request(url: str, headers: dict = None, retries: int = 10):
    """GET request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: get(url=url, headers=headers), retries=retries)

def post_request(url: str, headers: dict = None, data: dict = None, retries: int = 10):
    """POST request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        data (dict, optional): Request body. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: post(url=url, headers=headers, data=json.dumps(data)), retries=retries)

def put_request(url: str, headers: dict = None, retries: int = 10):
    """PUT request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: put(url=url, headers=headers), retries=retries)

def delete_request(url: str, headers: dict = None, data: dict = None, retries: int = 10):
    """DELETE request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        data (dict, optional): Request body. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: delete(url=url, headers=headers, data=json.dumps(data)), retries=retries)

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
    playlist_res = get_request(url=f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers)

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


def list_distance(a: 'list[int]', b: 'list[int]') -> int:
    """The weighted algorithm that calculates the distance between two songs according to either the distance between each song list of genres or the distance between each song list of artists


    Note:
        The "distance" is a mathematical value that represents how different two songs are, considering some parameter such as their genres or artists

    Note:
        For obvious reasons although both the parameters have two value options (genres, artists), when one of the parameters is specified as one of those, the other follows

    Args:
        a (list[int]): one song's list of genres or artists
        b (list[int]): counterpart song's list of genres or artists

    Returns:
        int: The distance between the two indexed lists
    """
    distance = 0
    for item_a, item_b in list(zip(a, b)):
        if item_a != item_b:
            if int(item_a) == 1:
                distance += 0.4
            else:
                distance += 0.2
        else:
            if int(item_a) == 1:
                distance -= 0.4

    return distance


def compute_distance(a: 'list[int]', b: 'list[int]', artist_recommendation: bool = False) -> float:
    """The portion of the algorithm that calculates the overall distance between two songs regarding the following:
    - genres: the difference between the two song's genres, using the list_distance function above
    - artists: the difference between the two song's artists, using the list_distance function above
    - popularity: the difference between the two song's popularity, considering it a basic absolute value from the actual difference between the values
    - danceability: Danceability describes how suitable a track is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity. A value of 0.0 is least danceable and 1.0 is most danceable.
    - energy: Energy is a measure from 0.0 to 1.0 and represents a perceptual measure of intensity and activity. Typically, energetic tracks feel fast, loud, and noisy. For example, death metal has high energy, while a Bach prelude scores low on the scale. Perceptual features contributing to this attribute include dynamic range, perceived loudness, timbre, onset rate, and general entropy.
    - instrumentalness: Predicts whether a track contains no vocals. "Ooh" and "aah" sounds are treated as instrumental in this context. Rap or spoken word tracks are clearly "vocal". The closer the instrumentalness value is to 1.0, the greater likelihood the track contains no vocal content
    - tempo: The overall estimated tempo of a track in beats per minute (BPM). In musical terminology, tempo is the speed or pace of a given piece and derives directly from the average beat duration.
    - valence: A measure from 0.0 to 1.0 describing the musical positiveness conveyed by a track. Tracks with high valence sound more positive (e.g. happy, cheerful, euphoric), while tracks with low valence sound more negative (e.g. sad, depressed, angry).

    Note:
        At the end there is a weighted multiplication of all the factors that implies two things:
         - They are in REALLY different scales
         - They have different importance levels to the final result of the calculation

    Args:
        a (list[int]): the song a, having all it's caracteristics
        b (list[int]): the song b, having all it's caracteristics

    Returns:
        float: the distance between the two songs
    # """

    genres_distance = list_distance(a['genres_indexed'], b['genres_indexed'])
    artists_distance = list_distance(a['artists_indexed'], b['artists_indexed'])
    popularity_distance = abs(a['popularity'] - b['popularity'])
    danceability_distance = abs(a['danceability'] - b['danceability'])
    energy_distance = abs(a['energy'] - b['energy'])
    instrumentalness_distance = abs(round(a['instrumentalness'], 2) - round(b['instrumentalness'], 2))
    tempo_distance = abs(a['tempo'] - b['tempo'])
    valence_distance = abs(a['valence'] - b['valence'])

    return (
        genres_distance * 0.8 +
        energy_distance * 0.6 +
        valence_distance * 0.9 +
        artists_distance * 0.38 +
        tempo_distance * 0.0025 +
        danceability_distance * 0.25 +
        instrumentalness_distance * 0.4 +
        popularity_distance * (0.015 if not artist_recommendation else 0.003)
    )


def playlist_exists(name: str, headers: dict) -> 'str|bool':
    """Function used to check if a playlist exists inside the user's library
    Used before the creation of a new playlist

    Args:
        name (str): name of the playlist being created, which could easily be bypassed, if the playlist names were not made automatically
        headers (dict): Request headers

    Returns:
        str|bool: If the playlist already exists, returns the id of the playlist, otherwise returns False
    """
    total_playlist_count = get_request(url=f'https://api.spotify.com/v1/me/playlists?limit=1', headers=headers).json()['total']
    playlists = []
    for offset in range(0, total_playlist_count, 50):
        request = get_request(url=f'https://api.spotify.com/v1/me/playlists?limit=50&{offset=!s}',  headers=headers).json()

        playlists += list(map(lambda playlist: (playlist['id'], playlist['name']), request['items']))

    for playlist in playlists:

        if playlist[1] == name:
            return playlist[0]

    return False


def create_playlist(type: str, headers: dict, user_id: str, additional_info: str = None) -> str:
    """Function that will return the empty playlist id, to be filled in later by the recommender songs
    This playlist may be a new one just created or a playlist that was previously created and now had all its songs removed

    Note:
        This function will change the user's library either making a new playlist or making an existing one empty

    Args:
        type (str): the type of the playlist being created ('song', 'short', 'medium'), meaning:\n
        --- 'song': a playlist related to a song\n
        --- 'short': a playlist related to the short term favorites for that given user\n
        --- 'medium': a playlist related to the medium term favorites for that given user\n
        --- 'most-listened-short': a playlist related to the short term most listened songs\n
        --- 'most-listened-medium': a playlist related to the medium term most listened songs\n
        --- 'most-listened-long': a playlist related to the long term most listened songs\n
        --- 'artist-related': a playlist related to a specific artist songs\n
        --- 'artist': a playlist containing only a specific artist songs\n

        headers (dict): Request headers
        user_id (str): Spotify User id
        additional_info (str, optional): name of the song, artist, or whatever additional information is needed. Defaults to None

    Raises:
        ValueError: The type argument musts be one of the valid options

    Returns:
        str: The playlist id
    """
    playlist_name = ''
    description = ''
    if type == 'song':
        playlist_name = f"{additional_info!r} Related"
        description = f"Songs related to {additional_info!r}"
    elif type in ['short', 'medium']:
        playlist_name = "Recent-ish Favorites" if type == 'medium' else "Latest Favorites"
        description = f"Songs related to your {type} term top 5"

    elif 'most-listened' in type:
        playlist_name = f"{type.replace('most-listened-', '').capitalize()} Term Most-listened Tracks"
        description = f"The most listened tracks in a {type.replace('most-listened-', '')} period of time"

    elif type == 'artist-related':
        playlist_name = f"{additional_info!r} Mix"
        description = f"Songs related to {additional_info!r}"

    elif type == 'artist':
        playlist_name = f"This once was {additional_info!r}"
        description = f'''{additional_info}'{"" if additional_info[-1] == "s" else "s"} songs'''
    else:
        raise ValueError('type not valid')
    new_id = ""
    playlist_id_found = playlist_exists(name=playlist_name, headers=headers)

    if playlist_id_found:
        new_id = playlist_id_found

        playlist_tracks = list(map(lambda track: {'uri': track['track']['uri']}, get_request(url=f'https://api.spotify.com/v1/playlists/{new_id}/tracks', headers=headers).json()['items']))

        delete_json = delete_request(url=f'https://api.spotify.com/v1/playlists/{new_id}/tracks', headers=headers, data={"tracks": playlist_tracks}).json()

    else:
        data = {
            "name": playlist_name,
            "description": description,
            "public": False
        }
        playlist_creation = post_request(url=f'https://api.spotify.com/v1/users/{user_id}/playlists', headers=headers, data=data)
        new_id = playlist_creation.json()['id']

    return new_id
