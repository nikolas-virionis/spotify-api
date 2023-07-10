import os
import re
import logging
import operator
import warnings
import pandas as pd
import spotify_recommender_api.util as util
import core as core
import spotify_recommender_api.auth.authentication as auth
import spotify_recommender_api.requests.request_handler as requests

from functools import reduce
from typing import Any, Union
from spotify_recommender_api.error import AccessTokenExpiredError

warnings.filterwarnings('error')


class SpotifyAPI:
    """
    Spotify API is the Class that provides access to the playlists recommendations
    """

    def __get_playlist_from_csv(self):
        """
        Function that creates the playlist variable from a CSV file previously created by this same package

        """

        try:
            df = pd.read_parquet(f'./.spotify-recommender-util/{self.__base_playlist_name}.parquet')
        except FileNotFoundError as e:
            try:
                df = pd.read_parquet('./.spotify-recommender-util/util.parquet')
                logging.warning(f'The playlist {self.__base_playlist_name} does not exist in the CSV format, but ever since the version 3.5.0 the csv file and the util file created, have the same name as the playlist, but there is only a generic file on your machine.')
                response = input('Therefore, do you want to rename the generic files to the new format, and therefore having the playlist name (y/n)? ')
                while response not in ['y', 'n']:
                    response = input('Select a valid option.\n Do you want to rename the generic files to the new format, and therefore having the playlist name (y/n)? ')

                if response == 'n':
                    raise FileNotFoundError(
                        'The playlist with the specified ID does not exist in the CSV format, try again but selecting the "web" option, as the source for the playlist') from e

                else:
                    self.__update_created_files = True

            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    'The playlist with the specified ID does not exist in the CSV format, try again but selecting the "web" option, as the source for the playlist') from exc

        self.__artists, self.__songs, self.__all_genres = [eval(arr) if isinstance(arr, str) else arr for arr in [df['artists'][0], df['songs'][0], df['all_genres'][0]]]

        if self.__update_created_files:
            self.__playlist = pd.read_csv('playlist.csv')
        else:
            self.__playlist = pd.read_csv(f'{self.__base_playlist_name}.csv')

    def __get_playlist(self):
        """
        General purpose function to get the playlist, either from CSV or web requests

        """
        answer = input('Do you want to get the playlist data via CSV saved previously or read from spotify, *which will take a few minutes* depending on the playlist size (csv/web)? ')
        while answer.lower() not in ['csv', 'web']:  # , 'parquet'
            answer = input("Please select a valid response: ")

        self.__update_created_files = False
        if answer.lower() == 'csv':
            self.__get_playlist_from_csv()
            return False

        return True

    def __get_song_genres(self, song: 'dict[str, Any]') -> 'list[str]':
        """
        Function that gets all the genres for a given song

        Args:
          song(dict[str, Any]): the song dictionary

        Returns:
          list[str]: list of genres for a given song
        """
        genres = []
        song_artists = song["track"]["artists"] if 'track' in list(song.keys()) else song["artists"]
        for artist in song_artists:
            artist_id = artist["id"]
            if artist_id not in self.__artists:
                artist_genres_res = requests.RequestHandler.get_request(url=f'https://api.spotify.com/v1/artists/{artist_id}')
                try:
                    artist_genres = artist_genres_res.json()["genres"]
                    genres += artist_genres
                    self.__artists[artist["name"]] = artist_genres
                except Exception as e:
                    logging.error(f'{e = }')
                    logging.debug(artist_genres_res.json())
            else:
                genres += self.__artists[artist_id]

        return list(set(genres))

    def __get_playlist_items(self):
        """
        Function that gets the items (songs) inside the playlist

        # Note
        Ran automatically but can last as long as 2.5 seconds for each song (can be worse depending on the network connection) inside of the playlist, not because it is compute demanding but because it needs to do a up to a handful of http requests per song, which can take a while

        """
        self.__all_genres = []
        try:
            total_song_count = util.get_total_song_count(playlist_id=self.__playlist_id)
            for offset in range(0, total_song_count, 100):
                logging.info(f'Songs mapped: {offset}/{total_song_count}')
                all_genres_res = requests.RequestHandler.get_request(
                    url=f'https://api.spotify.com/v1/playlists/{self.__playlist_id}/tracks?limit=100&{offset=!s}'
                )
                for song in all_genres_res.json()["items"]:
                    (id, name, popularity, artist, added_at), song_genres = util.song_data(song=song), self.__get_song_genres(song)
                    song['id'] = id
                    danceability, loudness, energy, instrumentalness, tempo, valence = util.query_audio_features(song=song)
                    self.__songs.append({
                        "id": id,
                        "name": name,
                        "artists": artist,
                        "popularity": popularity,
                        "genres": song_genres,
                        "added_at": added_at,
                        "danceability": danceability,
                        "loudness": loudness,
                        "energy": energy,
                        "instrumentalness": instrumentalness,
                        "tempo": tempo,
                        "valence": valence
                    })
                    self.__all_genres += song_genres

        except KeyError as e:
            raise ValueError(
                'Invalid Auth Token, try again with a valid one') from e

        else:
            self.__all_genres = list(set(self.__all_genres))

    def __get_liked_songs(self):
        """
        Function that gets the items (songs) inside the user's liked songs

        # Note
        Ran automatically but can last as long as 2.5 seconds for each song (can be worse depending on the network connection) inside of the playlist, not because it is compute demanding but because it needs to do a up to a handful of http requests per song, which can take a while

        """
        self.__all_genres = []

        total_song_count = requests.RequestHandler.get_request(url='https://api.spotify.com/v1/me/tracks').json()['total']

        for offset in range(0, total_song_count, 50):
            logging.info(f'Songs mapped: {offset}/{total_song_count}')
            all_genres_res = requests.RequestHandler.get_request(
                url=f'https://api.spotify.com/v1/me/tracks?limit=50&{offset=!s}'
            )
            for song in all_genres_res.json()["items"]:
                (id, name, popularity, artist, added_at), song_genres = util.song_data(
                    song=song), self.__get_song_genres(song)
                song['id'] = id
                danceability, loudness, energy, instrumentalness, tempo, valence = util.query_audio_features(
                    song=song)
                self.__songs.append({
                    "id": id,
                    "name": name,
                    "artists": artist,
                    "popularity": popularity,
                    "genres": song_genres,
                    "added_at": added_at,
                    "danceability": danceability,
                    "loudness": loudness,
                    "energy": energy,
                    "instrumentalness": instrumentalness,
                    "tempo": tempo,
                    "valence": valence
                })
                self.__all_genres += song_genres

        logging.info(f'Songs mapping complete: {total_song_count}/{total_song_count}')

        self.__all_genres: 'list[str]' = list(set(self.__all_genres))


    def __playlist_adjustments(self):
        """
        Function that does a bunch of adjustments to the overall formatting of the playlist, before making it visible

        """
        try:
            songs = self.__songs[-util.get_total_song_count(playlist_id=self.__playlist_id):]
        except KeyError as e:
            raise AccessTokenExpiredError('Invalid Auth Token, try again with a valid one') from e

        self.__all_artists = list(self.__artists.keys())
        playlist = pd.DataFrame(data=list(songs))

        playlist["genres_indexed"] = [
            util.item_list_indexed(
                all_items=self.__all_genres,
                items=eval(genre) if isinstance(genre, str) else genre,
            ) for genre in playlist["genres"]
        ]
        playlist["artists_indexed"] = [
            util.item_list_indexed(
                all_items=self.__all_artists,
                items=eval(artist) if isinstance(artist, str) else artist,
            ) for artist in playlist["artists"]
        ]
        playlist['id'] = playlist["id"].astype(str)
        playlist['name'] = playlist["name"].astype(str)
        playlist['popularity'] = playlist["popularity"].astype(int)
        playlist['added_at'] = pd.to_datetime(playlist["added_at"])
        playlist['danceability'] = playlist["danceability"].astype(float)
        playlist['energy'] = playlist["energy"].astype(float)
        playlist['instrumentalness'] = playlist["instrumentalness"].astype(float)
        playlist['tempo'] = playlist["tempo"].astype(float)
        playlist['valence'] = playlist["valence"].astype(float)
        if 'loudness' not in playlist.columns:
            playlist['loudness'] = 0
            logging.warning('Since version 4.3.0, there is a new column "loudness" and in order to get it you will need to get the playlist from web and not csv, after that everything will work just as before')

        playlist['loudness'] = playlist["loudness"].astype(float)
        self.__playlist = playlist

    def playlist_to_csv(self):
        """
        Function to convert playlist to CSV format
        Really useful if the package is being used in a .py file since it is not worth it to use it directly through web requests everytime even more when the playlist has not changed since last package usage
        """
        if not os.path.exists('./.spotify-recommender-util'):
            os.mkdir('./.spotify-recommender-util')

        df = pd.DataFrame(
            columns=['artists', 'songs', 'all_genres'],
            data=[
                {
                    'songs': self.__songs,
                    'artists': self.__artists,
                    'all_genres': self.__all_genres
                }
            ],
        )

        df.to_parquet(
            f'./.spotify-recommender-util/{self.__base_playlist_name}.parquet')

        playlist = self.__playlist[
            [
                'id',
                'name',
                'artists',
                'genres',
                'popularity',
                'added_at',
                'danceability',
                'loudness',
                'energy',
                'instrumentalness',
                'tempo',
                'valence'
            ]
        ]

        playlist.to_csv(f'{self.__base_playlist_name}.csv')

    def select_playlist(
            self,
            user_id: str,
            playlist_id: Union[str, None] = None,
            playlist_url: Union[str, None] = None,
            liked_songs: bool = False,
            prepare_favorites: bool = False
        ) -> None:
        """Function to select a playlist to be mapped and be available on all the playlist related recommendation functions

        Args:
            user_id (str): Spotify User ID
            playlist_id (str, optional): Playlist ID. Defaults to None.
            playlist_url (str, optional): Playlist Share URL (contains the ID, and it's easier to get). Defaults to None.
            liked_songs (bool, optional): Flag to use the user 'Liked songs' as the playlist. Defaults to False.
            prepare_favorites (bool, optional): Flag to prepare the deprecated functions for mid-term and short term favorites. Defaults to False.

        """
        self.__artists = {}
        self.__songs = []
        self.__deny_favorites = False
        if liked_songs:
            self.__playlist_id = 'liked_songs'

            self.__base_playlist_name = f'{user_id} Liked Songs'

        else:
            if playlist_id:
                self.__playlist_id = playlist_id
            else:
                if not playlist_url:
                    raise ValueError('Either the playlist url or its id must be specified')
                self.__playlist_id = util.playlist_url_to_id(url=playlist_url)
                self.__playlist_url = playlist_url

            self.__base_playlist_name = util.get_base_playlist_name(playlist_id=self.__playlist_id)

        logging.info('Mapping playlist items')

        if self.__get_playlist():
            if liked_songs:
                self.__get_liked_songs()
            else:
                self.__get_playlist_items()

        logging.info('Setting up some operations with the playlist')

        self.__playlist_adjustments()

        self.__song_dict = core.knn_prepared_data(playlist=self.__playlist)
        if prepare_favorites:
            self.__prepare_favorites_playlist()

        if self.__update_created_files:
            self.playlist_to_csv()

        self.__top_genres = self.__top_artists = self.__top_tracks = None



    def __init__(self, user_id: str, playlist_id: Union[str, None] = None, playlist_url: Union[str, None] = None, liked_songs: bool = False, prepare_favorites: bool = False):
        """Spotify API is the Class that provides access to the playlists recommendations

        Note:
            It will trigger most of the API functions and can take a good while to complete


        Args:
            auth_token (str): The authentication token for the Spotify API, base64 encoded string that allows the use of the API's functionalities
            user_id (str): The user ID, visible in the Spotify profile account settings
            playlist_id (str, optional): The playlist ID hash in Spotify. Defaults to None.
            playlist_url (str, optional): The url used while sharing the playlist. Defaults to None.

        Raises:
            ValueError: auth_token is required
            ValueError: Either the playlist url or its id must be specified
        """

        self.__user_id = user_id

        self.select_playlist(
            user_id=user_id,
            liked_songs=liked_songs,
            playlist_id=playlist_id,
            playlist_url=playlist_url,
            prepare_favorites=prepare_favorites
        )

    def __get_neighbors(self, song: int, K: int, song_dict: list, type: Union[str, None] = None) -> list:
        """Function thats using the distance calculated above, returns the K nearest neighbors for a given song

        Args:
            song (str): song's index in the songs list
            K (int): desired number K of neighbors to be returned
            song_dict (list): the list of songs
            type (str, optional): Neighbor playlist type. Defaults to None.

        Returns:
            list: list neighbors
        """
        if type is None:
            return []

        distances = []

        for song_index, song_value in enumerate(song_dict):
            if song_index != song:
                dist = core.compute_distance(song_a=song_dict[song], song_b=song_value, artist_recommendation='artist' in type)
                distances.append((song_index, dist))

        distances.sort(key=operator.itemgetter(1))
        return [[*distances[x]] for x in range(K)]

    def __get_index_for_song(self, song: Union[str, 'list[str]', None]) -> int:
        """Function that returns the index of a given song in the list of songs

        Args:
            song (str): song name

        Raises:
            ValueError: Playlist does not contain the song

        Returns:
            int: the index for the song
        """
        if song not in self.__playlist['name'].tolist():
            raise ValueError(f'Playlist does not contain the song {song!r}')

        item = self.__playlist.index[self.__playlist['name'] == song].tolist()

        return item[0]


    def __push_songs_to_playlist(self, full_uris: str, playlist_id: Union[str, bool, None]):
        """Function to push soongs to a specified playlist

        Args:
            full_uris (str): list of song uri's
            playlist_id (str): playlist id
        """
        full_uris_list = full_uris.split(',')

        if len(full_uris_list) <= 100:
            uris = ','.join(full_uris_list)
            add_songs_req = requests.RequestHandler.post_request(url=f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?{uris=!s}')

        else:

            for offset in range(0, len(full_uris_list), 100):

                uris = ','.join(full_uris_list[offset:offset + min(len(full_uris_list) - offset, 100)])
                add_songs_req = requests.RequestHandler.post_request(url=f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?{uris=!s}')


    def __build_playlist(self, type: str, uris: str, **kwargs):
        """Function that builds the contents of a playlist

        Note:
            This function will change the user's library by filling the previously created empty playlist

        Args:
            type (str): the type of the playlist being created
            uris (str): string containing all song uris in the format the Spotify API expects
        """
        if not uris:
            raise ValueError('Invalid value for the song uris')

        additional_information_by_type = {
            'song': {'song_name': getattr(self, '_SpotifyAPI__song_name', None)},
            'artist': {'artist_name': getattr(self, '_SpotifyAPI__artist_name', None)},
            'mood': {
                'mood': getattr(self, '_SpotifyAPI__mood', None),
                'exclude_mostly_instrumental': getattr(self, '_SpotifyAPI__exclude_mostly_instrumental', None),
            },
            'profile-recommendation': {
                'criteria': getattr(self, '_SpotifyAPI__profile_recommendation_criteria', None),
                'date': getattr(self, '_SpotifyAPI__profile_recommendation_date', None),
                'time_range': getattr(self, '_SpotifyAPI__profile_recommendation_time_range', None)
            },
            'playlist-recommendation': {
                'criteria': getattr(self, '_SpotifyAPI__playlist_recommendation_criteria', None),
                'date': getattr(self, '_SpotifyAPI__playlist_recommendation_date', None),
                'time_range': getattr(self, '_SpotifyAPI__playlist_recommendation_time_range', None)
            },
            'general-recommendation': {
                'description': getattr(self, '_SpotifyAPI__general_recommendation_description', None),
                'description_types': getattr(self, '_SpotifyAPI__general_recommendation_description_types', None)
            },
            'most-listened-recommendation': {'time_range': getattr(self, '_SpotifyAPI__most_listened_recommendation_time_range', None)},
        }


        playlist_id = core.create_playlist(
            type=type,
            user_id=self.__user_id,
            base_playlist_name=self.__base_playlist_name,
            **kwargs
        )

        self.__push_songs_to_playlist(full_uris=uris, playlist_id=playlist_id)

    def __write_playlist(self, type: str, K: int, additional_info: Union[str, 'list[str]', None] = None):
        """Function that writes a new playlist with the recommendations for the given type
        type: the type of the playlist being created ('song', 'short', 'medium'):
         - 'song': a playlist related to a song
         - 'short': a playlist related to the short term favorites for that given user
         - 'medium': a playlist related to the medium term favorites for that given user

        Note:
            This function will change the user's library by either creating a new plalylist or overriding the existing one

        Args:
            type (str): the type of the playlist being created
            K (int): desired number K of neighbors to be returned
            additional_info (Any, optional): the song name when the type is 'song'. Defaults to None.

        Raises:
            ValueError: Value for K must be between 1 and 1500
            ValueError: Invalid type
        """
        if K > 1500:
            logging.warning('K limit exceded. Maximum value for K is 1500')
            K = 1500
        elif K < 1:
            raise ValueError(f'Value for K must be between 1 and 1500 on creation of {type} playlist. {additional_info=!r}')

        if type == 'song':
            index = self.__get_index_for_song(additional_info)
            uris = f'spotify:track:{self.__song_dict[index]["id"]},'

            uris += ','.join([f'spotify:track:{neighbor}' for neighbor in self.__get_recommendations('song', additional_info, K)['id']])

        elif type in {'medium', 'short'}:
            ids = self.__medium_fav['id'] if type == 'medium' else self.__short_fav['id']

            uris = ','.join([f'spotify:track:{song}' for song in ids])

        elif any(x in type for x in ['most-listened', 'artist', '-recommendation', 'mood']):
            ids = additional_info
            if ids is None: # only because of strict type checking enforncing that if it can be None it souldnt be part of an iteration
                ids = []
            uris = ','.join([f'spotify:track:{song}' for song in ids])

        else:
            uris = ''
            raise ValueError('Invalid type')

        self.__build_playlist(type=type, uris=uris)

    def get_recommendations_for_song(
        self,
        K: int,
        song: str,
        generate_csv: bool = False,
        with_distance: bool = False,
        build_playlist: bool = False,
        generate_parquet: bool = False,
        print_base_caracteristics: bool = False
    ) -> Union[pd.DataFrame, None]:
        """Playlist which centralises the actions for a recommendation made for a given song

        Note
            The build_playlist option when set to True will change the user's library


        Args:
            K (int): desired number K of neighbors to be returned
            song (str): The desired song name
            generate_csv (bool, optional): Whether to generate a CSV file containing the recommended playlist. Defaults to False.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            generate_parquet (bool, optional): Whether to generate a parquet file containing the recommended playlist. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. Defaults to False.

        Raises:
            ValueError: Value for K must be between 1 and 1500

        Returns:
            pd.DataFrame: Pandas DataFrame containing the song recommendations
        """
        try:
            if not (1 < K <= 1500):
                raise ValueError(
                    f'Value for K must be between 1 and 1500 on creation of recommendation for the song {song}')

            self.__song_name = song

            df = self.__get_recommendations('song', song, K)
            playlist_name = f'{song} Related'

            if print_base_caracteristics:
                index = self.__get_index_for_song(song)
                caracteristics = self.__song_dict[index]
                name, genres, artists, popularity, _, danceability, loudness, energy, instrumentalness, tempo, valence = list(caracteristics.values())[1:11]
                util.print_base_caracteristics(name, genres, artists, popularity, danceability, loudness, energy, instrumentalness, tempo, valence)

            if generate_csv:
                df.to_csv(f'{playlist_name}.csv')

            if generate_parquet:
                df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

            if build_playlist:
                self.__write_playlist('song', K, additional_info=song)

            return df if with_distance else df.drop(columns=['distance'])

        except ValueError as e:
            logging.error(e)

    def __get_desired_dict_fields(self, index: int, song_dict: Union['list[dict[str, Any]]', None] = None) -> 'list[str]':
        """Function that returns the usual fields for a given song

        Args:
            index (int): The index of the song inside the song list
            song_dict (list, optional): song dictionary. Defaults to None.

        Returns:
            list[str]: list of fields of the desired song
        """

        if song_dict is None:
            song_dict = self.__song_dict

        desired_song_dict = song_dict[index]

        return [
            desired_song_dict['id'],
            desired_song_dict['name'],
            desired_song_dict['artists'],
            desired_song_dict['genres'],
            desired_song_dict['popularity'],
            desired_song_dict['added_at'],
            desired_song_dict['danceability'],
            desired_song_dict['loudness'],
            desired_song_dict['energy'],
            desired_song_dict['instrumentalness'],
            desired_song_dict['tempo'],
            desired_song_dict['valence']
        ]

    def __song_list_to_df(self, neighbors: list, song_dict: Union['list[dict[str, Any]]', None] = None) -> pd.DataFrame:
        """Function that returns DataFrame representation of the list of neighbor songs

        Args:
            neighbors (list): list of a given song's neighbors
            song_dict (list, optional): song dictionary. Defaults to None.

        Returns:
            pd.DataFrame: Song DataFrame
        """
        data = [list(self.__get_desired_dict_fields(neighbor[0], song_dict=song_dict) + [neighbor[1]]) for neighbor in neighbors]

        return pd.DataFrame(data=data, columns=['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence', 'distance'])

    def __get_recommendations(self, type: str, info, K: int = 51) -> pd.DataFrame:
        """General purpose function to get recommendations for any type supported by the package

        Args:
            info (Any): the changed song_dict list if the type is short or medium or else it is the name of the song to get recommendations from
            K (int, optional): desired number K of neighbors to be returned. Defaults to 51.
            type (str): the type of the playlist being created ('song', 'short', 'medium'), meaning:

            --- 'song': a playlist related to a song

            --- 'short': a playlist related to the short term favorites for that given user

            --- 'medium': a playlist related to the medium term favorites for that given user

            --- 'artist-related': a playlist related to a specific artist


        Raises:
            ValueError: Type does not correspond to a valid option

        Returns:
            pd.DataFrame: song DataFrame
        """
        index = 0
        if type == 'song':
            index = self.__get_index_for_song(info)
        elif type in {'long', 'medium', 'short', 'artist-related'}:
            index = len(info) - 1
        else:
            raise ValueError('Type does not correspond to a valid option')
        song_dict = self.__song_dict if type == 'song' else info
        neighbors = self.__get_neighbors(song=index, K=K, song_dict=song_dict, type=type)
        return self.__song_list_to_df(neighbors, song_dict=song_dict)

    def __get_genres(self, genres: 'list[list[str]]') -> 'list[str]':
        """Function to unite all the genres from different songs into one list of genres

        Args:
            genres (list[list[str]]): the list of lists of genres from the different songs

        Raises:
            ValueError: Playlist chosen does not correspond to any of the users favorite songs

        Returns:
            list[str]: full list of genres
        """
        try:
            all_genres = genres[0][:]
        except IndexError as e:
            self.__deny_favorites = True
            raise ValueError('Playlist chosen does not correspond to any of the users favorite songs') from e

        for index in range(1, len(genres)):
            for i in range(len(all_genres)):
                all_genres[i] = all_genres[i] or genres[index][i]

        return all_genres

    def __get_artists(self, artists: 'list[list[str]]') -> 'list[str]':
        """Function to unite all the artists from different songs into one list of artists

        Args:
            artists (list[list[str]]): the list of lists of artists from the different songs

        Raises:
            ValueError: Playlist chosen does not correspond to any of the users favorite songs

        Returns:
            list[str]: full list of artists
        """
        try:
            all_artists = artists[0][:]
        except IndexError as e:
            raise ValueError(
                'Playlist chosen does not correspond to any of the users favorite songs') from e

        for index in range(1, len(artists)):
            for i in range(len(all_artists)):
                all_artists[i] = all_artists[i] or artists[index][i]

        return all_artists

    def __get_top_5(self, time_range='medium') -> 'list[dict[str, Any]]':
        """Function that gets and initially formats the top 5 songs in a given time_range

        Args:
            time_range (str, optional): The time range to get the top 5 songs from ('medium', 'short'). Defaults to 'medium'.

        Raises:
            ValueError: time_range must be either medium_term or short_term

        Returns:
            list[dict[str, Any]]: top 5 songs listened
        """
        if time_range not in ['medium', 'short']:
            raise ValueError('time_range must be either medium_term or short_term')

        top_5 = requests.RequestHandler.get_request(url=f'https://api.spotify.com/v1/me/top/tracks?{time_range=!s}_term&limit=5').json()

        return [
            {
                'name': song['name'],
                'genres': self.__get_song_genres(song),
                'artists': [artist['name'] for artist in song['artists']],
                'popularity': song['popularity'],
                'danceability': self.__playlist.drop_duplicates('id').query('id == @song["id"]')['danceability'],
                'loudness': self.__playlist.drop_duplicates('id').query('id == @song["id"]')['loudness'],
                'energy': self.__playlist.drop_duplicates('id').query('id == @song["id"]')['energy'],
                'instrumentalness': self.__playlist.drop_duplicates('id').query('id == @song["id"]')['instrumentalness'],
                'tempo': self.__playlist.drop_duplicates('id').query('id == @song["id"]')['tempo'],
                'valence': self.__playlist.drop_duplicates('id').query('id == @song["id"]')['valence']
            }
            for song in top_5['items']
            if song['name'] in self.__playlist['name'].tolist()
        ]


    def __find_recommendations_to_songs(self, base_songs: 'list[dict[str, Any]]', subset_name: str) -> 'dict[str, Any]':
        """Generates a song format record from a list of songs, with all the information the "song-based" recommendation needs

        Args:
            base_songs (list[dict[str, Any]]): List of base songs
            subset_name (str): Name of thihs subset of songs (barely seen, unless the dataframe is printed with this record in it)

        Returns:
            dict[str, Any]: New song fomat record with the information gathered from the list of base songs
        """
        temp_genres = list(reduce(lambda acc, x: acc + list(set(x['genres']) - set(acc)), base_songs, []))

        temp_artists = list(reduce(lambda acc, x: acc + list(set(x['artists']) - set(acc)), base_songs, []))

        latest_fav = {
            'id': "",
            'name': subset_name,
            'genres': temp_genres,
            'artists': temp_artists,
            'genres_indexed': self.__get_genres([util.item_list_indexed(song['genres'], all_items=self.__all_genres) for song in base_songs])
        }

        latest_fav['artists_indexed'] = self.__get_artists([util.item_list_indexed(song['artists'], all_items=self.__all_artists) for song in base_songs])

        latest_fav['popularity'] = int(round(reduce(lambda acc, song: acc + int(song['popularity']), base_songs, 0) / len(base_songs)))

        latest_fav['danceability'] = float(reduce(lambda acc, song: acc + float(song['danceability']), base_songs, 0) / len(base_songs))

        latest_fav['loudness'] = float(reduce(lambda acc, song: acc + float(song['loudness']), base_songs, 0) / len(base_songs))

        latest_fav['energy'] = float(reduce(lambda acc, song: acc + float(song['energy']), base_songs, 0) / len(base_songs))

        latest_fav['instrumentalness'] = float(reduce(lambda acc, song: acc + float(song['instrumentalness']), base_songs, 0) / len(base_songs))

        latest_fav['tempo'] = float(reduce(lambda acc, song: acc + float(song['tempo']), base_songs, 0) / len(base_songs))

        latest_fav['valence'] = float(reduce(lambda acc, song: acc + float(song['valence']), base_songs, 0) / len(base_songs))

        return latest_fav

    def __prepare_fav_data(self, term: str) -> 'dict[str, Any]':
        """Function that expands on the formatting of the top_5 some time_range favorites

        Args:
            term (str): The time range to get the top 5 songs from ('medium', 'short')

        Returns:
            dict[str,]: recommendations for the favorite songs
        """
        top_5_songs = self.__get_top_5(term)

        return self.__find_recommendations_to_songs(
            base_songs=top_5_songs,
            subset_name="Recent-ish Favorites" if term == 'medium' else "Latest Favorites"
        )

    def __end_prepared_fav_data(self, type: str) -> 'list[dict[str, Any]]':
        """Final preparation for favorite data before getting visible

        Args:
            type (str): Playlist creation type

        Returns:
            list[dict[str,]]: song dictionary
        """
        song_dict = self.__song_dict[:]
        fav = self.__prepare_fav_data(type)
        song_dict.append(fav)
        return song_dict

    def get_playlist(self) -> pd.DataFrame:
        """Function that returns the playlist as pandas DataFrame with the needed, human readable, columns

        Returns:
            pd.DataFrame: Playlist DataFrame
        """
        return self.__playlist[['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence']]

    @util.deprecated
    def get_short_term_favorites_playlist(
        self,
        generate_csv: bool = False,
        with_distance: bool = False,
        build_playlist: bool = False,
        generate_parquet: bool = False,
    ) -> Union[pd.DataFrame, None]:
        """###DEPRECATED METHOD###\n
        Playlist which centralises the actions for a recommendation made for top 5 songs short term

        Note
            The build_playlist option when set to True will change the user's library

        Args:
            generate_csv (bool, optional): Whether to generate a CSV file containing the recommended playlist. Defaults to False.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs. Defaults to False.
            build_playlist (bool, optional): Whether to generate a parquet file containing the recommended playlist. Defaults to False.
            generate_parquet (bool, optional): Whether to build the playlist to the user's library. Defaults to False.

        Returns:
            pd.DataFrame: Short term favorites DataFrame
        """
        if self.__deny_favorites:
            logging.error("The chosen playlist does not contain the user's favorite songs")
            return
        df = self.__short_fav
        playlist_name = 'Latest Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if build_playlist:
            self.__write_playlist('short', 51)

        return df if with_distance else df.drop(columns=['distance'])

    @util.deprecated
    def get_medium_term_favorites_playlist(
            self,
            with_distance: bool = False,
            generate_csv: bool = False,
            generate_parquet: bool = False,
            build_playlist: bool = False
        ) -> Union[pd.DataFrame, None]:
        """###DEPRECATED METHOD###\n
        Playlist which centralises the actions for a recommendation made for top 5 songs medium term

        Note
            The build_playlist option when set to True will change the user's library

        Args:
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs. Defaults to False.
            generate_csv (bool, optional): Whether to generate a CSV file containing the recommended playlist. Defaults to False.
            generate_parquet (bool, optional): Whether to generate a parquet file containing the recommended playlist. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.

        Returns:
            pd.DataFrame: Medium term favorites DataFrame
        """
        if self.__deny_favorites:
            logging.error("The chosen playlist does not contain the user's favorite songs")
            return
        df = self.__medium_fav
        playlist_name = 'Recent-ish Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if build_playlist:
            self.__write_playlist('medium', 51)

        return df if with_distance else df.drop(columns=['distance'])

    def __prepare_favorites_playlist(self):
        """###DEPRECATED METHOD###\n
        Note: Although this method and the whole medium and short term favorite category is deprecated, this method will stil run, since somebody may want to use it. Having that said, I do not recommend it

        Automatic creation of both the favorites related recommendations
        """
        try:
            self.__short_fav = self.__get_recommendations('short',  self.__end_prepared_fav_data('short'))
            self.__medium_fav = self.__get_recommendations('medium',  self.__end_prepared_fav_data('medium'))
        except ValueError:
            return

    def get_most_listened(self, time_range: str = 'long', K: int = 50, build_playlist: bool = False) -> pd.DataFrame:
        """Function that creates the most-listened songs playlist for a given period of time in the users profile

        Args:
            time_range (str, optional): time range ('long', 'medium', 'short'). Defaults to 'long'.
            K (int, optional): Number of the most listened songs to return. Defaults to 50.

        Raises:
            ValueError: time range does not correspond to a valid time range ('long', 'medium', 'short')
            ValueError: Value for K must be between 1 and 1500


        Returns:
            pd.DataFrame: pandas DataFrame containing the top K songs in the time range
        """
        if time_range not in ['long', 'medium', 'short']:
            raise ValueError('time_range must be long, medium or short')

        if not (1 < K <= 1500):
            raise ValueError(f'Value for K must be between 1 and 1500: {time_range} term most listened')

        top = requests.RequestHandler.get_request(url=f'https://api.spotify.com/v1/me/top/tracks?{time_range=!s}_term&limit={K}').json()

        top_songs = [
            {
                'id': song['id'],
                'name': song['name'],
                'popularity': song['popularity'],
                'genres': self.__get_song_genres(song),
                'artists': [artist['name'] for artist in song['artists']]
            }
            for song in top['items']
        ]

        if build_playlist:
            self.__write_playlist(f'most-listened-{time_range}', K, additional_info=[x['id'] for x in top_songs])


        return pd.DataFrame(
            data=[
                {
                    'name': x['name'],
                    'genres': x['genres'],
                    'artists': x['artists'],
                    'popularity': x['popularity']
                }
                for x in top_songs
            ],
            columns=['name', 'artists', 'genres', 'popularity']
        )

    def __playlist_needs_update(self, playlist: 'tuple[str, str, str, str]', playlist_types_to_update: 'list[str]') -> bool:
        """Function to determine if a playlist inside the user's library needs to be updated

        Args:
            playlist (tuple[str, str, str, str]): Playlist information
            playlist_types_to_update (list[str]): Playlist types to be updated

        Returns:
            bool: The flag that indicates whether the playlist should be updated or not
        """
        _, name, description, _ = playlist

        if name in {'Long Term Most-listened Tracks', 'Medium Term Most-listened Tracks', 'Short Term Most-listened Tracks'} and 'most-listened-tracks' in playlist_types_to_update:
            return True

        elif (
            ' - 20' not in name and
            'Profile Recommendation' in name and
            any(
                playlist_type in playlist_types_to_update
                for playlist_type in {'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}
            )
        ):
            return True

        elif f', within the playlist {self.__base_playlist_name}' in description or self.__update_created_files:
            if (re.match(r"\'(.*?)\' Related", name) or re.match(r'\"(.*?)\" Related', name)) and 'song-related' in playlist_types_to_update:
                return True

            elif (re.match(r"\'(.*?)\' Mix", name) or re.match(r'\"(.*?)\" Mix', name)) and 'artist-mix' in playlist_types_to_update:
                return True

            elif (re.match(r"This once was \'(.*?)\'", name) or re.match(r'This once was \"(.*?)\"', name)) and 'artist-full' in playlist_types_to_update:
                return True

            elif 'Playlist Recommendation' in name and ' - 20' not in name and 'playlist-recommendation' in playlist_types_to_update:
                return True

            elif 'Songs related to the mood' in description and 'mood' in playlist_types_to_update:
                return True

            elif 'most listened recommendations' in name and 'most-listened-recommendation' in playlist_types_to_update:
                return True

        return False

    def update_all_generated_playlists(
            self, *,
            K: Union[int, None] = None,
            playlist_types_to_update: Union['list[str]', None] = None,
            playlist_types_not_to_update: Union['list[str]', None] = None
        ) -> None:
        """Update all package generated playlists in batch

        Note:
            It is NOT recommended to use the K parameter in this function, unless 100% on purpose, since it will make all the playlists have the same number of songs in them

        Arguments:
            K (int, optional): Number of songs in the new playlists, if not set, defaults to the number of songs already in the playlist. Defaults to None.
            playlist_types_to_update (list[str], optional): List of playlist types to update. For example, if you only want to update song-related playlists use this argument as ['song-related']. Defaults to all == ['most-listened-tracks', 'song-related', 'artist-mix', 'artist-full', 'playlist-recommendation', 'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation', 'mood', 'most-listened-recommendation'].
            playlist_types_not_to_update (list[str], optional): List of playlist types not to update. For example, if you want to update all playlists but song-related playlists use this argument as ['song-related']. it can be used alongside with the playlist_types_to_update but it can become confusing or redundant. Defaults to none == [].
        """
        if playlist_types_to_update is None:
            playlist_types_to_update = ['most-listened-tracks', 'song-related', 'artist-mix', 'artist-full', 'playlist-recommendation', 'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation', 'mood', 'most-listened-recommendation']

        if playlist_types_not_to_update is None:
            playlist_types_not_to_update = []

        playlist_types_to_update = [playlist_type for playlist_type in playlist_types_to_update if playlist_type not in playlist_types_not_to_update]

        if 'profile-recommendation' in playlist_types_to_update:
            logging.info('After version 4.4.0, the profile-recommendation playlists are separated in short, medium and long term. See the update_all_created_playlists docstring or the documentation at: https://github.com/nikolas-virionis/spotify-api')
            playlist_types_to_update.remove('profile-recommendation')
            for playlist_type in {'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}:
                if playlist_type not in playlist_types_to_update:
                    playlist_types_to_update.append(playlist_type)

        if 'profile-recommendation' in playlist_types_not_to_update:
            for playlist_type in {'profile-recommendation', 'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}:
                if playlist_type in playlist_types_to_update:
                    playlist_types_to_update.remove(playlist_type)

        total_playlist_count = requests.RequestHandler.get_request(url='https://api.spotify.com/v1/me/playlists?limit=0').json()['total']

        playlists = []

        for offset in range(0, total_playlist_count, 50):
            request = requests.RequestHandler.get_request(url=f'https://api.spotify.com/v1/me/playlists?limit=50&{offset=!s}').json()

            playlists += [(playlist['id'], playlist['name'], playlist['description'], playlist['tracks']['total']) for playlist in request['items']]

        playlists = [
                playlist
                for playlist in playlists
                if self.__playlist_needs_update(
                        playlist=playlist,
                        playlist_types_to_update=playlist_types_to_update
                )
            ]

        last_printed_perc_update = 0

        for index, (playlist_id, name, description, total_tracks) in enumerate(playlists):
            try:
                logging.debug(f'Updating song {name} - {index}/{len(playlists)}')
                if last_printed_perc_update + 10 <= (perc_update := next((perc for perc in range(100, 0, -10) if (100 * index) / len(playlists) >= perc), 100)) < 100:
                    logging.info(f'Playlists update operation at {perc_update}%')
                    last_printed_perc_update = perc_update

                if K is not None:
                    total_tracks = K

                if name in {'Long Term Most-listened Tracks', 'Medium Term Most-listened Tracks', 'Short Term Most-listened Tracks'} and 'most-listened-tracks' in playlist_types_to_update:
                    self.get_most_listened(time_range=name.split(" ")[0].lower(), K=total_tracks, build_playlist=True)

                elif f', within the playlist {self.__base_playlist_name}' in description or self.__update_created_files:
                    if (re.match(r"\'(.*?)\' Related", name) or re.match(r'\"(.*?)\" Related', name)) and 'song-related' in playlist_types_to_update:
                        song_name = name.replace(" Related", '')[1:-1]
                        self.__song_name = song_name
                        self.__write_playlist(type='song', K=total_tracks - 1, additional_info=song_name)

                    elif (re.match(r"\'(.*?)\' Mix", name) or re.match(r'\"(.*?)\" Mix', name)) and 'artist-mix' in playlist_types_to_update:
                        artist_name = name.replace(" Mix", '')[1:-1]
                        self.__artist_name = artist_name
                        self.artist_specific_playlist(
                            K=total_tracks,
                            build_playlist=True,
                            artist_name=artist_name,
                            complete_with_similar=True,
                            _auto=True
                        )

                    elif (re.match(r"This once was \'(.*?)\'", name) or re.match(r'This once was \"(.*?)\"', name)) and 'artist-full' in playlist_types_to_update:
                        artist_name = name.replace("This once was ", '')[1:-1]
                        self.__artist_name = artist_name
                        self.artist_specific_playlist(
                            K=total_tracks,
                            build_playlist=True,
                            artist_name=artist_name,
                            complete_with_similar=False,
                            ensure_all_artist_songs=f'All {artist_name}' in description,
                            _auto=True
                        )

                    # elif name == 'Recent-ish Favorites':
                    #     self.__write_playlist(type='medium', K=total_tracks)

                    # elif name == 'Latest Favorites':
                    #     self.__write_playlist(type='short', K=total_tracks)

                    elif 'Playlist Recommendation' in name and ' - 20' not in name and 'playlist-recommendation' in playlist_types_to_update:
                        criteria = name.split('(')[1].split(')')[0]
                        if ',' in criteria:
                            criteria = 'mixed'

                        time_range = 'all_time' if 'for all_time' in name else name.split('for the last')[-1].split('(')[0].strip()

                        self.get_playlist_recommendation(
                            K=total_tracks,
                            build_playlist=True,
                            time_range=time_range,
                            main_criteria=criteria,
                        )

                    elif 'Songs related to the mood' in description and 'mood' in playlist_types_to_update:
                        mood = ' '.join(name.split(' ')[:-1]).lower()

                        exclude_mostly_instrumental = 'excluding the mostly instrumental songs' in description

                        self.get_songs_by_mood(
                            mood=mood,
                            K=total_tracks,
                            build_playlist=True,
                            exclude_mostly_instrumental=exclude_mostly_instrumental,
                        )

                    elif 'most listened recommendations' in name and 'most-listened-recommendation' in playlist_types_to_update:
                        time_range = '_'.join(name.split(' ')[:2]).lower()

                        self.playlist_songs_based_on_most_listened_tracks(
                            K=total_tracks,
                            build_playlist=True,
                            time_range=time_range,
                        )

                elif (
                    ' - 20' not in name and
                    'Profile Recommendation' in name and
                    any(
                        playlist_type in playlist_types_to_update
                        for playlist_type in {'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}
                    )
                ):
                    criteria = name.split('(')[1].split(')')[0]
                    criteria_name = criteria

                    if ',' in criteria:
                        criteria = 'mixed'

                    if 'term' in name.lower():
                        time_range = '_'.join(name.split(' ')[1:3]).lower()
                    else:
                        time_range = 'short_term'
                        playlist_name = f"{time_range.replace('_', ' ').capitalize()} Profile Recommendation ({criteria_name})"
                        description = f'''{time_range.replace('_', ' ').capitalize()} Profile-based recommendations based on favorite {criteria_name}'''

                        data = {
                            "name": playlist_name,
                            "description": description,
                            "public": False
                        }

                        logging.info(f'Updating the name and description of the playlist {name} because of new time range specifications added to the profile_recommendation function in version 4.4.0')
                        logging.info('In case of any problems with the feature, submit an issue at: https://github.com/nikolas-virionis/spotify-api/issues')

                        update_playlist_details = requests.RequestHandler.put_request(url=f'https://api.spotify.com/v1/playlists/{playlist_id}', data=data)

                    if f"{time_range.replace('_', '-')}-profile-recommendation" not in playlist_types_to_update:
                        continue

                    self.get_profile_recommendation(
                        K=total_tracks,
                        build_playlist=True,
                        time_range=time_range,
                        main_criteria=criteria,
                    )

            except ValueError as e:
                logging.error(f"Unfortunately we couldn't update a playlist because\n {e}")

        logging.info('Playlists update operation at 100%')

    def get_playlist_trending_genres(self, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> Union[pd.DataFrame, None]:
        """Calculates the amount of times each genre was spotted in the playlist, and can plot a bar chart to represent this information

        Args:
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            plot_top(int|bool , optional): the number of top genres to be plotted. Must be 5, 10, 15 or False. No chart will be plotted if set to False. Defaults to False.

        Raises:
            ValueError: If the time_range parameter is not valid the error is raised.
            ValueError: If plot_top parameter is not valid the error is raised.

        Returns:
            pd.DataFrame: The dictionary that contains how many times each genre was spotted in the playlist in the given time range.
        """
        if time_range not in ['all_time', 'month', 'trimester', 'semester', 'year']:
            raise ValueError('time_range must be one of the following: "all_time", "month", "trimester", "semester", "year"')

        if plot_top and plot_top > 30:
            raise ValueError('plot_top must be either an int smaller than 30 or False')

        playlist = self.__playlist[self.__playlist['added_at'] > util.get_datetime_by_time_range(time_range=time_range)]

        if not len(playlist):
            logging.warning(f"No songs added to the playlist in the time range {time_range} ")
            return None

        genres = list(reduce(lambda x, y: list(x) + list(y), playlist['genres'], []))

        genres_dict = dict(reduce(lambda x, y: util.list_to_count_dict(dictionary=x, item=y), genres, {}))

        genres_dict['total'] = len(playlist['genres'])

        genres_dict = dict(sorted(genres_dict.items(), key=lambda x: x[1], reverse=True))

        genres_dict = util.value_dict_to_value_and_percentage_dict(dictionary=genres_dict)

        dictionary = {'name': [], 'number of songs': [], 'rate': []}

        for key, value in genres_dict.items():
            dictionary['name'].append(key)
            dictionary['number of songs'].append(value['value'])
            dictionary['rate'].append(value['percentage'])

        df = pd.DataFrame(data=dictionary, columns=['name', 'number of songs', 'rate'])

        if plot_top:
            core.plot_bar_chart(
                df=df,
                top=plot_top,
                plot_max=reduce(lambda x, y: x + y, df['rate'][1:4], 0) >= 0.50
            )

        return df

    def get_playlist_trending_artists(self, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> Union[pd.DataFrame, None]:
        """Calculates the amount of times each artist was spotted in the playlist, and can plot a bar chart to represent this information

        Args:
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            plot_top(int|bool , optional): the number of top genres to be plotted. No chart will be plotted if set to False. Defaults to False.

        Raises:
            ValueError: If the time_range parameter is not valid the error is raised.

        Returns:
            pd.DataFrame: The dictionary that contains how many times each artist was spotted in the playlist in the given time range.
        """
        if time_range not in ['all_time', 'month', 'trimester', 'semester', 'year']:
            raise ValueError(
                'time_range must be one of the following: "all_time", "month", "trimester", "semester", "year"')

        if plot_top and plot_top > 30:
            raise ValueError(
                'plot_top must be either an int smaller than 30 or False')

        playlist = self.__playlist[self.__playlist['added_at'] >
                                   util.get_datetime_by_time_range(time_range=time_range)]

        if not len(playlist):
            logging.warning(f"No songs added to the playlist in the time range {time_range} ")
            return None

        artists = list(reduce(lambda x, y: list(x) + list(y), playlist['artists'], []))

        artists_dict = dict(reduce(lambda x, y: util.list_to_count_dict(
            dictionary=x, item=y), artists, {}))

        artists_dict['total'] = len(playlist['artists'])

        artists_dict = dict(sorted(artists_dict.items(),
                            key=lambda x: x[1], reverse=True))

        artists_dict = util.value_dict_to_value_and_percentage_dict(
            dictionary=artists_dict)

        dictionary = {'name': [], 'number of songs': [], 'rate': []}

        for key, value in artists_dict.items():
            dictionary['name'].append(key)
            dictionary['number of songs'].append(value['value'])
            dictionary['rate'].append(value['percentage'])

        df = pd.DataFrame(data=dictionary, columns=[
                          'name', 'number of songs', 'rate'])

        if plot_top:
            core.plot_bar_chart(df=df, top=plot_top, plot_max=reduce(
                lambda x, y: x + y, df['rate'][1:4], 0) >= 0.50)

        return df

    def artist_specific_playlist(
        self,
        artist_name: str,
        K: int = 50,
        with_distance: bool = False,
        build_playlist: bool = False,
        complete_with_similar: bool = False,
        ensure_all_artist_songs: bool = True,
        print_base_caracteristics: bool = False,
        _auto: bool = False
    ) -> pd.DataFrame:  # sourcery skip: extract-method
        """Function that generates DataFrame containing only a specific artist songs, with the possibility of completing it with the closest songs to that artist

        Args:
            artist_name (str): The name of the artist
            K (int, optional): Maximum number of songs. Defaults to 50.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since it does not obey any actual unit, it is just a mathematical value to determine the closet songs. ONLY TAKES EFFECT IF complete_with_similar == True AND K > NUMBER_OF_SONGS_WITH_THAT_ARTIST. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            ensure_all_artist_songs (bool, optional): Whether to ensure that all artist songs are in the playlist, regardless of the K number specified. Defaults to True
            complete_with_similar (bool, optional): Flag to complete the list of songs with songs that are similar to that artist, until the K number is reached. Only applies if K is greater than the number of songs by that artist in the playlist. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. ONLY TAKES EFFECT IF complete_with_similar == True AND K > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.

        Raises:
            ValueError: Value for K must be between 1 and 1500
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """
        if not (1 < K <= 1500):
            raise ValueError(
                f'Value for K must be between 1 and 1500 for the {artist_name} {"Mix" if complete_with_similar else "specific playlist"}')

        artist_songs = self.__playlist[self.__playlist['artists'].str.contains(
            artist_name, regex=False)]

        if not len(artist_songs):
            raise ValueError(
                f'{artist_name = } does not exist in the playlist')

        self.__artist_name = artist_name

        columns = ['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence']

        if complete_with_similar:
            artist_songs_record_song_dict = [{
                    'id': '',
                    'name': song['name'],
                    'artists': song['artists'],
                    'genres': song['genres'],
                    'artists_indexed': song['artists_indexed'],
                    'genres_indexed': song['genres_indexed'],
                    'popularity': song['popularity'],
                    'added_at': song['added_at'],
                    'danceability': song['danceability'],
                    'loudness': song['loudness'],
                    'energy': song['energy'],
                    'instrumentalness': song['instrumentalness'],
                    'tempo': song['tempo'],
                    'valence': song['valence']
                }
                for song in [
                    song
                    for song in self.__song_dict
                    if artist_name in song['artists']
                ]
            ]

            artist_songs_record = self.__find_recommendations_to_songs(base_songs=artist_songs_record_song_dict, subset_name=f"{artist_name} Mix")

            song_dict = [{
                    'id': song['id'],
                    'name': song['name'],
                    'artists': song['artists'],
                    'genres': song['genres'],
                    'artists_indexed': song['artists_indexed'],
                    'genres_indexed': song['genres_indexed'],
                    'popularity': song['popularity'],
                    'added_at': song['added_at'],
                    'danceability': song['danceability'],
                    'loudness': song['loudness'],
                    'energy': song['energy'],
                    'instrumentalness': song['instrumentalness'],
                    'tempo': song['tempo'],
                    'valence': song['valence']
                }
                for song in [
                    song
                    for song in self.__song_dict
                    if artist_name in song['artists']
                ]
            ]

            song_dict.append(artist_songs_record)

            mix_songs = self.__get_recommendations('artist-related', song_dict, K=K-len(artist_songs) if len(artist_songs) < K else len(artist_songs) // 3)

            ids = pd.concat([artist_songs['id'], mix_songs['id']]).tolist()

            if with_distance:
                df = artist_songs[columns]

                columns.append('distance')

                df['distance'] = pd.to_numeric(0)

                df = pd.concat([df[columns], mix_songs[columns]])

            else:
                df = pd.concat([artist_songs[columns], mix_songs[columns]])

            if print_base_caracteristics and not _auto:
                name = artist_songs_record['name']
                genres = artist_songs_record['genres']
                artists = artist_songs_record['artists']
                popularity = artist_songs_record['popularity']
                danceability = artist_songs_record['danceability']
                loudness = artist_songs_record['loudness']
                energy = artist_songs_record['energy']
                instrumentalness = artist_songs_record['instrumentalness']
                tempo = artist_songs_record['tempo']
                valence = artist_songs_record['valence']
                util.print_base_caracteristics(name, genres, artists, popularity, danceability, loudness, energy, instrumentalness, tempo, valence)

        elif not _auto and len(artist_songs) < K:
            logging.info(f'Playlist has only {len(artist_songs)} songs')
            logging.info(f'To fill the {K = } number of songs, consider using the flag complete_with_similar')
            ids = artist_songs['id'].tolist()
            df = artist_songs[columns]

        elif ensure_all_artist_songs:
            ids = artist_songs['id'].tolist()
            df = artist_songs[columns]

        else:
            ids = artist_songs['id'][:K].tolist()
            df = artist_songs[columns][:K]

        if build_playlist:
            self.__write_playlist(
                K=K,
                type=f'artist{"-related" if complete_with_similar else "-full" if ensure_all_artist_songs else ""}',
                additional_info=ids
            )

        return df.reset_index(drop=True)

    def audio_features_extraordinary_songs(self) -> 'dict[str, dict]':
        """Returns a dictionary with the maximum and minimum values for each audio feature used in the package

        Note:
            Although there are many more audio features available in Spotify Web API, these were the only ones needed to provide the best fitting recommendations within this package

        Note:
            The Audio features are:
            - danceability: Danceability describes how suitable a track is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity. A value of 0.0 is least danceable and 1.0 is most danceable.
            - energy: Energy is a measure from 0.0 to 1.0 and represents a perceptual measure of intensity and activity. Typically, energetic tracks feel fast, loud, and noisy. For example, death metal has high energy, while a Bach prelude scores low on the scale. Perceptual features contributing to this attribute include dynamic range, perceived loudness, timbre, onset rate, and general entropy.
            - instrumentalness: Predicts whether a track contains no vocals. "Ooh" and "aah" sounds are treated as instrumental in this context. Rap or spoken word tracks are clearly "vocal". The closer the instrumentalness value is to 1.0, the greater likelihood the track contains no vocal content
            - tempo: The overall estimated tempo of a track in beats per minute (BPM). In musical terminology, tempo is the speed or pace of a given piece and derives directly from the average beat duration.
            - valence: A measure from 0.0 to 1.0 describing the musical positiveness conveyed by a track. Tracks with high valence sound more positive (e.g. happy, cheerful, euphoric), while tracks with low valence sound more negative (e.g. sad, depressed, angry).

        Returns:
            dict[str, dict]: The dictionary with the maximum and minimum values for each audio feature used in the package
        """
        df = self.__playlist[['id', 'name', 'artists', 'genres', 'popularity','added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence']]

        df_danceability = df.sort_values('danceability', ascending=True)
        df_loudness = df.sort_values('loudness', ascending=True)
        df_energy = df.sort_values('energy', ascending=True)
        df_instrumentalness = df.sort_values('instrumentalness', ascending=True)
        df_tempo = df.sort_values('tempo', ascending=True)
        df_valence = df.sort_values('valence', ascending=True)
        max_danceability = df_danceability.tail(n=1).reset_index(drop=True)
        min_danceability = df_danceability.head(n=1).reset_index(drop=True)
        max_loudness = df_loudness.tail(n=1).reset_index(drop=True)
        min_loudness = df_loudness.head(n=1).reset_index(drop=True)
        max_energy = df_energy.tail(n=1).reset_index(drop=True)
        min_energy = df_energy.head(n=1).reset_index(drop=True)
        max_instrumentalness = df_instrumentalness.tail(n=1).reset_index(drop=True)
        min_instrumentalness = df_instrumentalness.head(n=1).reset_index(drop=True)
        max_tempo = df_tempo.tail(n=1).reset_index(drop=True)
        min_tempo = df_tempo.head(n=1).reset_index(drop=True)
        max_valence = df_valence.tail(n=1).reset_index(drop=True)
        min_valence = df_valence.head(n=1).reset_index(drop=True)

        return {
            'max_loudness': {
                'id': max_loudness['id'][0],
                'name': max_loudness['name'][0],
                'genres': max_loudness['genres'][0],
                'artists': max_loudness['artists'][0],
                'popularity': max_loudness['popularity'][0],
                'added_at': max_loudness['added_at'][0],
                'danceability': max_loudness['danceability'][0],
                'loudness': max_loudness['loudness'][0],
                'energy': max_loudness['energy'][0],
                'instrumentalness': max_loudness['instrumentalness'][0],
                'tempo': max_loudness['tempo'][0],
                'valence': max_loudness['valence'][0]
            },
            'min_loudness': {
                'id': min_loudness['id'][0],
                'name': min_loudness['name'][0],
                'genres': min_loudness['genres'][0],
                'artists': min_loudness['artists'][0],
                'popularity': min_loudness['popularity'][0],
                'added_at': min_loudness['added_at'][0],
                'danceability': min_loudness['danceability'][0],
                'loudness': min_loudness['loudness'][0],
                'energy': min_loudness['energy'][0],
                'instrumentalness': min_loudness['instrumentalness'][0],
                'tempo': min_loudness['tempo'][0],
                'valence': min_loudness['valence'][0]
            },
            'max_danceability': {
                'id': max_danceability['id'][0],
                'name': max_danceability['name'][0],
                'genres': max_danceability['genres'][0],
                'artists': max_danceability['artists'][0],
                'popularity': max_danceability['popularity'][0],
                'added_at': max_danceability['added_at'][0],
                'danceability': max_danceability['danceability'][0],
                'loudness': max_danceability['loudness'][0],
                'energy': max_danceability['energy'][0],
                'instrumentalness': max_danceability['instrumentalness'][0],
                'tempo': max_danceability['tempo'][0],
                'valence': max_danceability['valence'][0]
            },
            'min_danceability': {
                'id': min_danceability['id'][0],
                'name': min_danceability['name'][0],
                'genres': min_danceability['genres'][0],
                'artists': min_danceability['artists'][0],
                'popularity': min_danceability['popularity'][0],
                'added_at': min_danceability['added_at'][0],
                'danceability': min_danceability['danceability'][0],
                'loudness': min_danceability['loudness'][0],
                'energy': min_danceability['energy'][0],
                'instrumentalness': min_danceability['instrumentalness'][0],
                'tempo': min_danceability['tempo'][0],
                'valence': min_danceability['valence'][0]
            },
            'max_energy': {
                'id': max_energy['id'][0],
                'name': max_energy['name'][0],
                'genres': max_energy['genres'][0],
                'artists': max_energy['artists'][0],
                'popularity': max_energy['popularity'][0],
                'added_at': max_energy['added_at'][0],
                'danceability': max_energy['danceability'][0],
                'loudness': max_energy['loudness'][0],
                'energy': max_energy['energy'][0],
                'instrumentalness': max_energy['instrumentalness'][0],
                'tempo': max_energy['tempo'][0],
                'valence': max_energy['valence'][0]
            },
            'min_energy': {
                'id': min_energy['id'][0],
                'name': min_energy['name'][0],
                'genres': min_energy['genres'][0],
                'artists': min_energy['artists'][0],
                'popularity': min_energy['popularity'][0],
                'added_at': min_energy['added_at'][0],
                'danceability': min_energy['danceability'][0],
                'loudness': min_energy['loudness'][0],
                'energy': min_energy['energy'][0],
                'instrumentalness': min_energy['instrumentalness'][0],
                'tempo': min_energy['tempo'][0],
                'valence': min_energy['valence'][0]
            },
            'max_instrumentalness': {
                'id': max_instrumentalness['id'][0],
                'name': max_instrumentalness['name'][0],
                'genres': max_instrumentalness['genres'][0],
                'artists': max_instrumentalness['artists'][0],
                'popularity': max_instrumentalness['popularity'][0],
                'added_at': max_instrumentalness['added_at'][0],
                'danceability': max_instrumentalness['danceability'][0],
                'loudness': max_instrumentalness['loudness'][0],
                'energy': max_instrumentalness['energy'][0],
                'instrumentalness': max_instrumentalness['instrumentalness'][0],
                'tempo': max_instrumentalness['tempo'][0],
                'valence': max_instrumentalness['valence'][0]
            },
            'min_instrumentalness': {
                'id': min_instrumentalness['id'][0],
                'name': min_instrumentalness['name'][0],
                'genres': min_instrumentalness['genres'][0],
                'artists': min_instrumentalness['artists'][0],
                'popularity': min_instrumentalness['popularity'][0],
                'added_at': min_instrumentalness['added_at'][0],
                'danceability': min_instrumentalness['danceability'][0],
                'loudness': min_instrumentalness['loudness'][0],
                'energy': min_instrumentalness['energy'][0],
                'instrumentalness': min_instrumentalness['instrumentalness'][0],
                'tempo': min_instrumentalness['tempo'][0],
                'valence': min_instrumentalness['valence'][0]
            },
            'max_tempo': {
                'id': max_tempo['id'][0],
                'name': max_tempo['name'][0],
                'genres': max_tempo['genres'][0],
                'artists': max_tempo['artists'][0],
                'popularity': max_tempo['popularity'][0],
                'added_at': max_tempo['added_at'][0],
                'danceability': max_tempo['danceability'][0],
                'loudness': max_tempo['loudness'][0],
                'energy': max_tempo['energy'][0],
                'instrumentalness': max_tempo['instrumentalness'][0],
                'tempo': max_tempo['tempo'][0],
                'valence': max_tempo['valence'][0]
            },
            'min_tempo': {
                'id': min_tempo['id'][0],
                'name': min_tempo['name'][0],
                'genres': min_tempo['genres'][0],
                'artists': min_tempo['artists'][0],
                'popularity': min_tempo['popularity'][0],
                'added_at': min_tempo['added_at'][0],
                'danceability': min_tempo['danceability'][0],
                'loudness': min_tempo['loudness'][0],
                'energy': min_tempo['energy'][0],
                'instrumentalness': min_tempo['instrumentalness'][0],
                'tempo': min_tempo['tempo'][0],
                'valence': min_tempo['valence'][0]
            },
            'max_valence': {
                'id': max_valence['id'][0],
                'name': max_valence['name'][0],
                'genres': max_valence['genres'][0],
                'artists': max_valence['artists'][0],
                'popularity': max_valence['popularity'][0],
                'added_at': max_valence['added_at'][0],
                'danceability': max_valence['danceability'][0],
                'loudness': max_valence['loudness'][0],
                'energy': max_valence['energy'][0],
                'instrumentalness': max_valence['instrumentalness'][0],
                'tempo': max_valence['tempo'][0],
                'valence': max_valence['valence'][0]
            },
            'min_valence': {
                'id': min_valence['id'][0],
                'name': min_valence['name'][0],
                'genres': min_valence['genres'][0],
                'artists': min_valence['artists'][0],
                'popularity': min_valence['popularity'][0],
                'added_at': min_valence['added_at'][0],
                'danceability': min_valence['danceability'][0],
                'loudness': min_valence['loudness'][0],
                'energy': min_valence['energy'][0],
                'instrumentalness': min_valence['instrumentalness'][0],
                'tempo': min_valence['tempo'][0],
                'valence': min_valence['valence'][0]
            },
        }

    @util.deprecated
    def refresh_token(self, token: str):
        """###DEPRECATED METHOD###
        Refreshes the authorization token for the Spotify API, so that it is not necessary to rerun the entire script using the package to reauthenticate

        Args:
            token (str): Token generated from the Spotify API Console, with the following scopes:
             - user-top-read
             - playlist-library-read
             - playlist-read-private
             - playlist-library-modify
             - playlist-modify-private
        """
        headers = self.__headers
        headers['Authorization'] = f'Bearer {token}'

        requests.RequestHandler.get_request(url='https://api.spotify.com/v1/me/playlists?limit=0')

        self.__auth_token = token
        self.__headers = headers

    def audio_features_statistics(self) -> 'dict[str, float]':
        """FUnctions that returns the statistics (max, min and mean) for the audio features within the playlist

        Returns:
            dict[str, float]: The dictionary with the statistics
        """
        df: pd.DataFrame = self.__playlist[['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence']]

        return {
            'min_tempo': df['tempo'].min(),
            'max_tempo': df['tempo'].max(),
            'mean_tempo': df['tempo'].mean(),
            'min_energy': df['energy'].min(),
            'max_energy': df['energy'].max(),
            'mean_energy': df['energy'].mean(),
            'min_valence': df['valence'].min(),
            'max_valence': df['valence'].max(),
            'mean_valence': df['valence'].mean(),
            'min_danceability': df['danceability'].min(),
            'max_danceability': df['danceability'].max(),
            'mean_danceability': df['danceability'].mean(),
            'min_loudness': df['loudness'].min(),
            'max_loudness': df['loudness'].max(),
            'mean_loudness': df['loudness'].mean(),
            'min_instrumentalness': df['instrumentalness'].min(),
            'max_instrumentalness': df['instrumentalness'].max(),
            'mean_instrumentalness': df['instrumentalness'].mean(),
        }

    def get_profile_recommendation(
            self,
            K: int = 50,
            main_criteria: str = 'mixed',
            save_with_date: bool = False,
            build_playlist: bool = False,
            time_range: str = 'short_term'
        ) -> Union[pd.DataFrame, None]:
        """Builds a Profile based recommendation

        Args:
            K (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            main_criteria (str, optional): Main criteria for the recommendations playlist. Can be one of the following: 'mixed', 'artists', 'tracks', 'genres'. Defaults to 'mixed'.
            save_with_date (bool, optional): Flag to save the recommendations playlist as a Point in Time Snapshot. Defaults to False.
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.
            time_range (str, optional): The time range to get the profile most listened information from. Can be one of the following: 'short_term', 'medium_term', 'long_term'. Defaults to 'short_term'

        Raises:
            ValueError: K must be between 1 and 100
            ValueError: 'mixed', 'artists', 'tracks', 'genres'
            ValueError: time_range needs to be one of the following: 'short_term', 'medium_term', 'long_term'

        Returns:
            pd.DataFrame: Recommendations playlist
        """
        if not (1 < K <= 100):
            raise ValueError('K must be between 1 and 100')

        if main_criteria not in {'mixed', 'artists', 'tracks', 'genres'}:
            raise ValueError("main_criteria must be one of the following: 'mixed', 'artists', 'tracks', 'genres'")

        if time_range not in {'short_term', 'medium_term', 'long_term'}:
            raise ValueError("time_range needs to be one of the following: 'short_term', 'medium_term', 'long_term'")

        tracks = []
        genres = []
        artists = []

        if main_criteria != 'tracks':
            if self.__top_genres or self.__top_artists:
                genres = self.__top_genres
                artists = self.__top_artists

            else:
                top_artists_req = requests.RequestHandler.get_request(
                    url=f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=5',
                ).json()['items']

                artists = [artist['id'] for artist in top_artists_req]
                genres = list(set(reduce(lambda x, y: x + y, [artist['genres'] for artist in top_artists_req], [])))[:5]
                self.__top_genres = genres
                self.__top_artists = artists

        if main_criteria not in ['artists']:
            if self.__top_tracks:
                tracks = self.__top_tracks

            else:
                tracks = [
                    track['id']
                    for track in requests.RequestHandler.get_request(
                        url=f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=5'
                    ).json()['items']
                ]

                self.__top_tracks = tracks

        url = f'https://api.spotify.com/v1/recommendations?limit={K}'

        if main_criteria == 'artists' and artists is not None:
            url += f'&seed_artists={",".join(artists)}'
        elif main_criteria == 'genres' and genres is not None:
            url += f'&seed_genres={",".join(genres[:4])}&seed_tracks={",".join(tracks[:1])}'
        elif main_criteria == 'mixed' and genres is not None and artists is not None:
            url += f'&seed_tracks={",".join(tracks[:2])}&seed_artists={",".join(artists[:1])}&seed_genres={",".join(genres[:2])}'
        elif main_criteria == 'tracks':
            url += f'&seed_tracks={",".join(tracks)}'

        recommendations = requests.RequestHandler.get_request(url=url).json()

        if not recommendations.get("tracks"):
            logging.error(f'There was a problem creating the profile recommendations based on {main_criteria}')
            return

        songs = []

        for song in recommendations["tracks"]:
            (id, name, popularity, artist), song_genres = util.song_data(song=song, added_at=False), self.__get_song_genres(song)
            song['id'] = id
            danceability, loudness, energy, instrumentalness, tempo, valence = util.query_audio_features(song=song)
            songs.append({
                "id": id,
                "name": name,
                "artists": artist,
                "popularity": popularity,
                "genres": song_genres,
                "danceability": danceability,
                "loudness": loudness,
                "energy": energy,
                "instrumentalness": instrumentalness,
                "tempo": tempo,
                "valence": valence
            })

        recommendations_playlist = pd.DataFrame(data=songs)

        ids = recommendations_playlist['id'].tolist()

        if build_playlist:
            self.__profile_recommendation_date = save_with_date
            self.__profile_recommendation_time_range = time_range
            self.__profile_recommendation_criteria = main_criteria

            self.__write_playlist(
                K=K,
                type='profile-recommendation',
                additional_info=ids
            )

        return recommendations_playlist


    def get_playlist_recommendation(
        self,
        K: int = 50,
        time_range: str = 'all_time',
        main_criteria: str = 'mixed',
        save_with_date: bool = False,
        build_playlist: bool = False,
    ) -> Union[pd.DataFrame, None]:
        """Builds a playlist based recommendation

        Args:
            K (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            main_criteria (str, optional): Main criteria for the recommendations playlist. Can be one of the following: 'mixed', 'artists', 'tracks', 'genres'. Defaults to 'mixed'.
            save_with_date (bool, optional): Flag to save the recommendations playlist as a Point in Time Snapshot. Defaults to False.
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.

        Raises:
            ValueError: K must be between 1 and 100
            ValueError: 'mixed', 'artists', 'tracks', 'genres'

        Returns:
            pd.DataFrame: Recommendations playlist
        """

        if not (1 < K <= 100):
            raise ValueError('K must be between 1 and 100')

        if main_criteria not in ['mixed', 'artists', 'tracks', 'genres']:
            raise ValueError(
                "main_criteria must be one of the following: 'mixed', 'artists', 'tracks', 'genres'")

        tracks = []
        genres = []
        artists = []


        audio_statistics = self.audio_features_statistics()

        if main_criteria not in ['genres', 'tracks']:

            if (top_artists := self.get_playlist_trending_artists(time_range=time_range)) is None:
                return None

            top_artists_names = top_artists['name'][1:6].tolist()

            artists = [
                requests.RequestHandler.get_request(
                    url=f'https://api.spotify.com/v1/search?q={x}&type=artist&limit=1'
                ).json()['artists']['items'][0]['id']
                for x in top_artists_names
            ]

        if main_criteria not in ['artists']:
            if self.__top_tracks:
                tracks = self.__top_tracks

            else:
                tracks = [
                    track['id']
                    for track in requests.RequestHandler.get_request(
                        url='https://api.spotify.com/v1/me/top/tracks?time_range=short_term&limit=5',
                    ).json()['items']
                ]

                self.__top_tracks = tracks
        if main_criteria != 'artists':
            if (genres := self.get_playlist_trending_genres(time_range=time_range)) is None:
                return None

            genres = genres['name'][1:6].tolist()[:5]

        min_tempo = audio_statistics['min_tempo'] * 0.8
        max_tempo = audio_statistics['max_tempo'] * 1.2
        target_tempo = audio_statistics['mean_tempo']
        min_energy = audio_statistics['min_energy'] * 0.8
        max_energy = audio_statistics['max_energy'] * 1.2
        target_energy = audio_statistics['mean_energy']
        min_valence = audio_statistics['min_valence'] * 0.8
        max_valence = audio_statistics['max_valence'] * 1.2
        target_valence = audio_statistics['mean_valence']
        min_danceability = audio_statistics['min_danceability'] * 0.8
        max_danceability = audio_statistics['max_danceability'] * 1.2
        target_danceability = audio_statistics['mean_danceability']
        min_loudness = audio_statistics['min_loudness'] * 0.8
        max_loudness = audio_statistics['max_loudness'] * 1.2
        target_loudness = audio_statistics['mean_loudness']
        min_instrumentalness = audio_statistics['min_instrumentalness'] * 0.8
        max_instrumentalness = audio_statistics['max_instrumentalness'] * 1.2
        target_instrumentalness = audio_statistics['mean_instrumentalness']

        url = f'https://api.spotify.com/v1/recommendations?limit={K}'

        if main_criteria == 'artists':
            url += f'&seed_artists={",".join(artists)}'

        elif main_criteria == 'genres':
            url += f'&seed_genres={",".join(genres[:4])}&seed_tracks={",".join(tracks[:1])}'
        elif main_criteria == 'mixed':
            url += f'&seed_tracks={",".join(tracks[:1])}&seed_artists={",".join(artists[:2])}&seed_genres={",".join(genres[:2])}'
        elif main_criteria == 'tracks':
            url += f'&seed_tracks={",".join(tracks[:2])}&seed_genres={",".join(genres[:3])}'
        url += f'&{min_tempo=!s}&{max_tempo=!s}&{target_tempo=!s}&{min_energy=!s}&{max_energy=!s}&{target_energy=!s}&{min_valence=!s}&{max_valence=!s}&{target_valence=!s}&{min_danceability=!s}&{max_danceability=!s}&{target_danceability=!s}&{min_instrumentalness=!s}&{max_instrumentalness=!s}&{target_instrumentalness=!s}'

        recommendations = requests.RequestHandler.get_request(url=url).json()

        songs = []

        for song in recommendations["tracks"]:
            (id, name, popularity, artist), song_genres = util.song_data(song=song, added_at=False), self.__get_song_genres(song)
            song['id'] = id
            danceability, loudness, energy, instrumentalness, tempo, valence = util.query_audio_features(song=song)
            songs.append({
                "id": id,
                "name": name,
                "artists": artist,
                "popularity": popularity,
                "genres": song_genres,
                "danceability": danceability,
                "loudness": loudness,
                "energy": energy,
                "instrumentalness": instrumentalness,
                "tempo": tempo,
                "valence": valence
            })

        recommendations_playlist = pd.DataFrame(data=songs)

        ids = recommendations_playlist['id'].tolist()

        if build_playlist:
            self.__playlist_recommendation_date = save_with_date
            self.__playlist_recommendation_time_range = time_range
            self.__playlist_recommendation_criteria = main_criteria

            self.__write_playlist(
                K=K,
                type='playlist-recommendation',
                additional_info=ids
            )

        return recommendations_playlist


    def get_general_recommendation(
        self,
        K: int = 50,
        genres_info: Union['list[str]', None] = None,
        artists_info: Union['list[str]', None] = None,
        build_playlist: bool = False,
        use_main_playlist_audio_features: bool = False,
        tracks_info: Union['list[str]', 'list[tuple[str]]', 'list[list[str]]', 'dict[str, str]', None] = None,
    ) -> Union[pd.DataFrame, None]:
        """Builds a general recommendation based on up to 5 items spread across artists, genres, and tracks.

        Args:
            K (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            genres_info (list[str], optional): list of the genre names to be used in the recommendation. Defaults to [].
            artists_info (list[str], optional): list of the artist names to be used in the recommendation. Defaults to [].
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.
            use_main_playlist_audio_features (bool, optional): Flag to use the audio features of the main playlist to target better recommendations. Defaults to False.
            tracks_info (list[str] | list[tuple[str]] | list[list[str]] | dict[str, str]], optional): List of the song names to be used in the recommendations. They can be only the song names, but since there are a lot of songs with the same name i recommend using also the artist name in a key-value format using either a tuple, or list, or dict. Defaults to [].

        Raises:
            ValueError: K must be between 1 and 100
            ValueError: At least one of the three args must be provided: genres_info, artists_info, tracks_info
            ValueError: The sum of the number of items in each of the three args mustn't exceed 5
            ValueError: The argument tracks_info must be an instance of one of the following 4 types: list[str], list[tuple[str]], list[list[str]], dict[str, str]

        Returns:
            pd.DataFrame: Recommendations playlist
        """

        if not (1 < K <= 100):
            raise ValueError('K must be between 1 and 100')

        if not (genres_info or artists_info or tracks_info):
            raise ValueError('At least one of the three args must be provided: genres_info, artists_info, tracks_info')

        if genres_info is None:
            genres_info = []

        if artists_info is None:
            artists_info = []

        if tracks_info is None:
            tracks_info = []

        if len(genres_info) + len(artists_info) + len(tracks_info) > 5:
            raise ValueError('The sum of the number of items in each of the three args mustn\'t exceed 5')

        url = f'https://api.spotify.com/v1/recommendations?limit={K}'

        description = 'General Recommendation based on '

        types = []

        if artists_info:
            types.append('artists')
            description += 'the artists '
            for artist in artists_info:
                description += f'{artist}, '

            description = ' and '.join(description[:-2].rsplit(', ', 1))

            artists = [
                requests.RequestHandler.get_request(
                    url=f'https://api.spotify.com/v1/search?q={artist}&type=artist&limit=1',
                ).json()['artists']['items'][0]['id']
                for artist in artists_info
            ]

            url += f'&seed_artists={",".join(artists)}'

            if len(artists_info) == 1:
                description = description.replace('artists', 'artist')

        if genres_info:
            types.append('genres')
            url += f'&seed_genres={",".join(genres_info)}'

            if artists_info and not tracks_info:
                description += ', and the genres '
                final_sep = ''
            elif not artists_info and tracks_info:
                description += 'the genres '
                final_sep = ', and the tracks '
            elif not (artists_info or tracks_info):
                description += 'the genres '
                final_sep = ''
            else:  # both artists and tracks exist
                description += ', the genres '
                final_sep = ', and the tracks '

            for genre in genres_info:
                description += f'{genre}, '

            description = f"{' and '.join(description[:-2].rsplit(', ', 1)) if len(genres_info) > 1 else description[:-2]}{final_sep}"

            if len(genres_info) == 1:
                description = description.replace('genres', 'genre')

        if tracks_info:
            types.append('tracks')
            if artists_info and not genres_info:
                description += ', and the tracks '
            elif not artists_info and not genres_info:
                description += 'the tracks '

            if isinstance(tracks_info, dict):
                for song, artist in tracks_info.items():
                    description += f'{song} by {artist}, '

                tracks = [
                    requests.RequestHandler.get_request(
                        url=f'https://api.spotify.com/v1/search?q={song} {artist}&type=track&limit=1',
                    ).json()['tracks']['items'][0]['id']
                    for song, artist in tracks_info.items()
                ]

            elif isinstance(tracks_info[0], tuple) or isinstance(tracks_info[0], list):
                for song, artist in tracks_info: # type: ignore because of the strict typing not recognizing that the condition above makes this a safe operation
                    description += f'{song} by {artist}, '
                tracks = [
                    requests.RequestHandler.get_request(
                        url=f'https://api.spotify.com/v1/search?q={song} {artist}&type=track&limit=1',
                    ).json()['tracks']['items'][0]['id']
                    for song, artist in tracks_info # type: ignore because of the strict typing not recognizing that the condition above makes this a safe operation
                ]

            elif isinstance(tracks_info[0], str):
                for song in tracks_info:
                    description += f'{song}, '
                tracks = [
                    requests.RequestHandler.get_request(
                        url=f'https://api.spotify.com/v1/search?q={song}&type=track&limit=1',
                    ).json()['tracks']['items'][0]['id']
                    for song in tracks_info
                ]

            else:
                raise ValueError('The argument tracks_info must be an instance of one of the following 4 types: list[str], list[tuple[str]], list[list[str]], dict[str, str]')

            description = ' and '.join(description[:-2].rsplit(', ', 1)) if len(artists_info) > 1 else description[:-2]

            url += f'&seed_tracks={",".join(tracks)}'

            if len(tracks_info) == 1:
                description = description.replace('tracks', 'track')

        if use_main_playlist_audio_features:

            audio_statistics = self.audio_features_statistics()

            min_tempo = audio_statistics['min_tempo'] * 0.8
            max_tempo = audio_statistics['max_tempo'] * 1.2
            target_tempo = audio_statistics['mean_tempo']
            min_energy = audio_statistics['min_energy'] * 0.8
            max_energy = audio_statistics['max_energy'] * 1.2
            target_energy = audio_statistics['mean_energy']
            min_valence = audio_statistics['min_valence'] * 0.8
            max_valence = audio_statistics['max_valence'] * 1.2
            target_valence = audio_statistics['mean_valence']
            min_danceability = audio_statistics['min_danceability'] * 0.8
            max_danceability = audio_statistics['max_danceability'] * 1.2
            target_danceability = audio_statistics['mean_danceability']
            min_loudness = audio_statistics['min_loudness'] * 0.8
            max_loudness = audio_statistics['max_loudness'] * 1.2
            target_loudness = audio_statistics['mean_loudness']
            min_instrumentalness = audio_statistics['min_instrumentalness'] * 0.8
            max_instrumentalness = audio_statistics['max_instrumentalness'] * 1.2
            target_instrumentalness = audio_statistics['mean_instrumentalness']

            url += f'&{min_tempo=!s}&{max_tempo=!s}&{target_tempo=!s}&{min_energy=!s}&{max_energy=!s}&{target_energy=!s}&{min_valence=!s}&{max_valence=!s}&{target_valence=!s}&{min_danceability=!s}&{max_danceability=!s}&{target_danceability=!s}&{min_instrumentalness=!s}&{max_instrumentalness=!s}&{target_instrumentalness=!s}'

        recommendations = requests.RequestHandler.get_request(url=url).json()

        songs = []

        for song in recommendations["tracks"]:
            (id, name, popularity, artist), song_genres = util.song_data(song=song, added_at=False), self.__get_song_genres(song)
            song['id'] = id
            danceability, loudness, energy, instrumentalness, tempo, valence = util.query_audio_features(song=song)
            songs.append({
                "id": id,
                "name": name,
                "artists": artist,
                "popularity": popularity,
                "genres": song_genres,
                "danceability": danceability,
                "loudness": loudness,
                "energy": energy,
                "instrumentalness": instrumentalness,
                "tempo": tempo,
                "valence": valence
            })

        recommendations_playlist = pd.DataFrame(data=songs)

        if build_playlist:
            ids = recommendations_playlist['id'].tolist()
            types = ' and '.join(', '.join(types).rsplit(
                ', ', 1)) if len(types) > 1 else types[0]
            self.__general_recommendation_description = description
            self.__general_recommendation_description_types = types

            self.__write_playlist(
                K=K,
                type='general-recommendation',
                additional_info=ids
            )

        return recommendations_playlist

    def get_songs_by_mood(
            self,
            mood: str,
            K: int = 50,
            build_playlist: bool = False,
            exclude_mostly_instrumental: bool = False
        ) -> pd.DataFrame:
        """Function to create playlists based on the general mood of a song

        Args:
            mood (str): The mood of the song. Can be 'happy', 'sad' or 'calm'
            K (int, optional): Number of songs. Defaults to 50.
            build_playlist (bool, optional): Flag to create the playlist in the user's library. Defaults to False.
            exclude_mostly_instrumental (bool, optional): Flag to exclude the songs which are 80% or more instrumental. Defaults to False.

        Raises:
            ValueError: If the mood is not one of the valid options the error is raised

        Returns:
            pd.DataFrame: A DataFrame containing the new playlist
        """
        if mood not in ['happy', 'sad', 'calm']: # energetic still needs work to be ready
            raise ValueError("The mood parameter must be one of the following: 'happy', 'sad', 'calm'")

        energy_threshold = 0.7
        valence_threshold = 0.5
        instrumentalness_threshold = 0.8

        mood_queries = {
            'sad': {
                'ascending': True,
                'sorting': 'energy&valence',
                'query': 'valence < @valence_threshold and energy < @energy_threshold'
            },
            'calm': {
                'ascending': True,
                'sorting': 'energy&loudness',
                'query': 'valence >= @valence_threshold and energy < @energy_threshold'
            },
            'angry': {
                'ascending': False,
                'sorting': 'energy&loudness',
                'query': 'valence < @valence_threshold and energy >= @energy_threshold'
            },
            'happy': {
                'ascending': False,
                'sorting': 'energy&valence',
                'query': 'valence >= @valence_threshold and energy >= @energy_threshold'
            }
        }

        playlist = self.__playlist.query(mood_queries[mood]['query']).copy()

        if mood_queries[mood]['sorting'] == 'energy&valence':
            playlist['mood_index'] = playlist['energy'] + 3 * playlist['valence']
        else:
            playlist['mood_index'] = playlist['energy'] + 3 * playlist['loudness']
        # this is necessary because of the moods that are not consistent in terms of the conditions applied to energy and valence, for example, happy and sad which have the same condition applied to both thresholds can use both in the sorting whereas the others can't.

        if exclude_mostly_instrumental:
            playlist = playlist.query('instrumentalness <= @instrumentalness_threshold')

        playlist = playlist.sort_values(by='mood_index', ascending=mood_queries[mood]['ascending'])

        if len(playlist) >= K:
            playlist = playlist[:K]
        else:
            K = len(playlist)
            logging.warning(f'The playlist does not contain {K} {mood} songs. Therefore there are only {len(playlist)} in the returned playlist. ')

        if build_playlist:
            self.__mood = mood
            self.__exclude_mostly_instrumental = exclude_mostly_instrumental
            ids = playlist['id'].tolist()

            self.__write_playlist(
                K=K,
                type=f'mood',
                additional_info=ids
            )

        return playlist


    def playlist_songs_based_on_most_listened_tracks(
            self,
            K: int = 50,
            build_playlist: bool = False,
            time_range: str = 'short_term',
        ) -> Union[pd.DataFrame, None]:
        """Function to create a playlist with songs from the base playlist that are the closest to the user's most listened songs

        Args:
            K (int, optional): Number of songs. Defaults to 50.
            build_playlist (bool, optional): Flag to create the playlist in the user's library. Defaults to False.
            time_range (str, optional): String to identify which is the time range, could be one of the following: {'short_term', 'medium_term', 'long_term'}. Defaults to 'short_term'.

        Raises:
            ValueError: time_range needs to be one of the following: 'short_term', 'medium_term', 'long_term'

        Returns:
            Union[pd.DataFrame, None]: DataFrame that contains the information of all songs in the new playlist
        """
        if time_range not in {'short_term', 'medium_term', 'long_term'}:
            raise ValueError("time_range needs to be one of the following: 'short_term', 'medium_term', 'long_term'")

        top_50 = requests.RequestHandler.get_request(url=f'https://api.spotify.com/v1/me/top/tracks?{time_range=!s}&limit=50').json()

        top_50 = [
            {
                'id': song['id'],
                'name': song['name'],
                'genres': self.__get_song_genres(song),
                'artists': [artist['name'] for artist in song['artists']],
                'popularity': song['popularity']
            }
            for song in top_50['items']
        ]

        for song in top_50:
            danceability, loudness, energy, instrumentalness, tempo, valence = util.query_audio_features(song=song)

            song.update({ # not using **song because the id isnt needed
                'danceability': danceability,
                'loudness': loudness,
                'energy': energy,
                'instrumentalness': instrumentalness,
                'tempo': tempo,
                'valence': valence,
            })


        most_listened_recommendation = {
            'id': "UNOFFICIAL_ID",
            'name': f"{time_range.replace('_', ' ').capitalize()} Most Listened",
            'genres': list(reduce(lambda acc, x: acc + x['genres'], top_50, [])),
            'artists': list(reduce(lambda acc, x: acc + x['artists'], top_50, [])),
            'popularity': int(round(reduce(lambda acc, song: acc + int(song['popularity']), top_50, 0) / len(top_50))),
            'genres_indexed': self.__get_genres([util.item_list_indexed(song['genres'], all_items=self.__all_genres) for song in top_50]),
            'artists_indexed': self.__get_artists([util.item_list_indexed(song['artists'], all_items=self.__all_artists) for song in top_50]),
        }

        for audio_feature in ['danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence']:
            most_listened_recommendation[audio_feature] = float(reduce(lambda acc, song: acc + float(song[audio_feature]), top_50, 0) / len(top_50))

        song_dict = [*self.__song_dict, most_listened_recommendation]

        playlist = self.__get_recommendations(type=time_range.split('_')[0], info=song_dict, K=K)

        if build_playlist:
            ids = playlist['id'].tolist()
            self.__most_listened_recommendation_time_range = time_range

            self.__write_playlist(
                K=K,
                type=f'most-listened-recommendation',
                additional_info=ids
            )

        return playlist


def start_api(user_id: str, *, playlist_url: Union[str, None] = None, playlist_id: Union[str, None] = None, liked_songs: bool = False, log_level: str = 'INFO', prepare_favorites: bool = False):
    """Function that prepares for and initializes the API

    Note:
        Internet Connection is required

    Args:
        user_id(str): the id of user, present in the user account profile

    Keyword Arguments:
        playlist_url(str, optional, keyword-argument only): the url for the playlist, which is visible when trying to share it. Defaults to False.
        playlist_id (str, optional, keyword-argument only): the id of the playlist, an unique big hash which identifies the playlist. Defaults to False.
        liked_songs (bool, optional, keyword-argument only): A flag to identify if the playlist to be mapped is the Liked Songs. Defaults to False.
        prepare_favorites (bool, optional, keyword-argument only): A flag to identify if the Short and Medium term favorite playlists will be calculated. IMPORTANT to note that both are DEPRECATED. Defaults to False.

    Raises:
        ValueError: at least one of the playlist related arguments have to be specified
        ValueError: when asked to input the auth token, in case it is not valid, an error is raised
        ValueError: when passing the arguments, there should be only one filled between playlist_url, playlist_id and liked_songs

    Returns:
        SpotifyAPI: The instance of the SpotifyAPI class

    Note:
    Although both the playlist_url and playlist_id are optional, informing at least one of them is required, though the choice is up to you
    """
    if log_level.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        raise ValueError("log_level must be one of the following: 'DEBUG', 'INFO', 'WARNING', 'ERROR'")

    logging.basicConfig(
        level=log_level.upper(),
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s',
    )

    logger = logging.getLogger('spotify-recommender-api')

    if (playlist_url is not None or playlist_id is not None) and liked_songs or (playlist_url is not None and playlist_id is not None):
        raise ValueError('It is necessary to specify only one or none of the following parameters: playlist_id or playlist_url or liked_songs')

    logging.info('Retrieving Authentication token')

    requests.RequestHandler.get_auth()

    return SpotifyAPI(playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url, liked_songs=liked_songs, prepare_favorites=prepare_favorites)