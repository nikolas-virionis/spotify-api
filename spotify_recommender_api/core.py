import pytz
import datetime
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import spotify_recommender_api.util as util
import spotify_recommender_api.requests as requests
sns.set()


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
    for item_a, item_b in zip(a, b):
        if item_a != item_b:
            distance += 0.4 if int(item_a) == 1 else 0.2
        elif int(item_a) == 1:
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
        popularity_distance * (0.003 if artist_recommendation else 0.015)
    )


def create_playlist(type: str, headers: dict, user_id: str, base_playlist_name: str, additional_info: str = None, _update_created_playlists: bool = False) -> str:
    """Function that will return the empty playlist id, to be filled in later by the recommender songs
    This playlist may be a new one just created or a playlist that was previously created and now had all its songs removed

    Note:
        This function will change the user's library either making a new playlist or making an existing one empty

    Args:
        headers (dict): Request headers
        user_id (str): Spotify User id
        base_playlist_name (str): name of the base playlist
        additional_info (str, optional): name of the song, artist, or whatever additional information is needed. Defaults to None\n
        type (str): the type of the playlist being created ('song', 'short', 'medium'), meaning:\n
        --- 'song': a playlist related to a song\n
        --- 'short': a playlist related to the short term favorites for that given user\n
        --- 'medium': a playlist related to the medium term favorites for that given user\n
        --- 'most-listened-short': a playlist related to the short term most listened songs\n
        --- 'most-listened-medium': a playlist related to the medium term most listened songs\n
        --- 'most-listened-long': a playlist related to the long term most listened songs\n
        --- 'artist-related': a playlist related to a specific artist songs\n
        --- 'artist': a playlist containing only a specific artist songs\n

    Raises:
        ValueError: The type argument musts be one of the valid options

    Returns:
        str: The playlist id
    """

    if type == 'song':
        playlist_name = f"{additional_info!r} Related"
        description = f"Songs related to {additional_info!r}, within the playlist {base_playlist_name}"
    elif type in {'short', 'medium'}:
        playlist_name = "Recent-ish Favorites" if type == 'medium' else "Latest Favorites"
        description = f"Songs related to your {type} term top 5, within the playlist {base_playlist_name}"

    elif 'most-listened' in type:
        playlist_name = f"{type.replace('most-listened-', '').capitalize()} Term Most-listened Tracks"
        description = f"The most listened tracks in a {type.replace('most-listened-', '')} period of time"

    elif type == 'artist-related':
        playlist_name = f"{additional_info!r} Mix"
        description = f"Songs related to {additional_info!r}, within the playlist {base_playlist_name}"

    elif type == 'artist-full':
        playlist_name = f"This once was {additional_info!r}"
        description = f'''All {additional_info}'{"" if additional_info[-1] == "s" else "s"} songs, within the playlist {base_playlist_name}'''

    elif type == 'artist':
        playlist_name = f"This once was {additional_info!r}"
        description = f'''{additional_info}'{"" if additional_info[-1] == "s" else "s"} songs, within the playlist {base_playlist_name}'''

    elif type == 'profile-recommendation':
        criteria = additional_info[0] if additional_info[0] != 'mixed' else 'genres, tracks and artists'
        playlist_name = "Profile Recommendation"
        description = f'''Profile-based recommendations based on favorite {criteria}'''

        if additional_info[1]:
            now = datetime.datetime.now(tz=pytz.timezone('UTC'))
            playlist_name += f' ({criteria} - {now.strftime("%Y-%m-%d")})'
            description += f' - {now.strftime("%Y-%m-%d")} snapshot'
        else:
            playlist_name += f' ({criteria})'

    elif type == 'playlist-recommendation':
        criteria = additional_info[0] if additional_info[0] != 'mixed' else 'genres, tracks and artists'
        time_range = f'for the last {additional_info[2]}' if additional_info[2] != 'all_time' else 'for all_time'
        playlist_name = f"Playlist Recommendation {time_range}"
        description = f'''Playlist-based recommendations based on favorite {criteria}, within the playlist {base_playlist_name} {time_range}'''

        if additional_info[1]:
            now = datetime.datetime.now(tz=pytz.timezone('UTC'))
            playlist_name += f' ({criteria} - {now.strftime("%Y-%m-%d")})'
            description += f' - {now.strftime("%Y-%m-%d")} snapshot'
        else:
            playlist_name += f' ({criteria})'
    else:
        raise ValueError('type not valid')

    if playlist_id_found := util.playlist_exists(name=playlist_name, base_playlist_name=base_playlist_name, headers=headers, _update_created_playlists=_update_created_playlists):
        new_id = playlist_id_found

        playlist_tracks = list(map(lambda track: {'uri': track['track']['uri']}, requests.get_request(url=f'https://api.spotify.com/v1/playlists/{new_id}/tracks', headers=headers).json()['items']))

        delete_json = requests.delete_request(url=f'https://api.spotify.com/v1/playlists/{new_id}/tracks', headers=headers, data={"tracks": playlist_tracks}).json()

        if _update_created_playlists:
            data = {
                "name": playlist_name,
                "description": description,
                "public": False
            }

            update_playlist_details = requests.put_request(url=f'https://api.spotify.com/v1/playlists/{new_id}', headers=headers, data=data)



    else:
        data = {
            "name": playlist_name,
            "description": description,
            "public": False
        }
        playlist_creation = requests.post_request(url=f'https://api.spotify.com/v1/users/{user_id}/playlists', headers=headers, data=data)
        new_id = playlist_creation.json()['id']

    return new_id

def create_playlist_data_dict(row) -> dict:
    """Function to be applied to the pandas DataFrame to create a dictionary with each row's information

    Args:
        row (Row): Row of the iteration on the Pandas DataFrame

    Returns:
        dict: Dictionary containing the data with the columns necessary for the use in KNN
    """
    return {
        'id': row['id'],
        'name': row['name'],
        'genres': row['genres'],
        'artists': row['artists'],
        'popularity': row['popularity'],
        'added_at': row['added_at'],
        'danceability': row['danceability'],
        'energy': row['energy'],
        'instrumentalness': row['instrumentalness'],
        'tempo': row['tempo'],
        'valence': row['valence'],
        'genres_indexed': row['genres_indexed'],
        'artists_indexed': row['artists_indexed']
    }

def knn_prepared_data(playlist: pd.DataFrame) -> 'list[dict[str,]]':
    """Function to prepare the data for the algorithm which calculates the distances between the songs

    Note:
        It will make a copy of the playlist to a list, to avoid changing the original DataFrame playlist.
        And also leave it in an easier to 'iterate over' format

    Args:
        playlist (pd.DataFrame): playlist to be prepared for the use of the knn algorithm

    Returns:
        list[dict[str,]]: list to be used by the algorithm based on the given playlist
    """
    data = playlist[
        [
            'id',
            'name',
            'genres',
            'artists',
            'popularity',
            'added_at',
            'danceability',
            'energy',
            'instrumentalness',
            'tempo',
            'valence',
            'genres_indexed',
            'artists_indexed'
        ]
    ].copy()

    data['track_dict'] = data.apply(create_playlist_data_dict, axis=1)

    return data['track_dict'].tolist()


def plot_bar_chart(df: pd.DataFrame, chart_title: str = None, top: int = 10, plot_max: bool = True):
    """Plot a bar Chart with the top values from the dictionary

    Args:
        df (pd.DataFrame): DataFrame to plotthat contains the data
        chart_title (str, optional): label of the chart. Defaults to None
        top (int, optional): numbers of values to be in the chart. Defaults to 10
    """

    if plot_max:
        df = df[df['name'] != ''][:top + 1]
    else:
        print(f'Total number of songs: {df["number of songs"][0]}')
        df = df[df['name'] != ''][1:top + 1]

    plt.figure(figsize=(15,10))

    sns.color_palette('bright')

    sns.barplot(x='name', y='number of songs', data=df, label=chart_title)

    plt.xticks(
        rotation=45,
        horizontalalignment='right',
        fontweight='light',
        fontsize='x-large'
    )

    plt.show()
