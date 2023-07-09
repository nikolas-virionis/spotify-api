import os
import re
import logging
import warnings
import pandas as pd
import spotify_recommender_api.util as util
import core as core

from functools import reduce, partial
from typing import Union, Any, Callable
from spotify_recommender_api.model.user import User
from spotify_recommender_api.playlist.playlist import Playlist
from spotify_recommender_api.playlist.liked_songs import LikedSongs
from spotify_recommender_api.requests.request_handler import RequestHandler

warnings.filterwarnings('error')


class SpotifyAPI:
    """
    Spotify API is the Class that provides access to the playlists recommendations
    """

    def __init__(self, user_id: str, playlist_id: Union[str, None] = None, playlist_url: Union[str, None] = None, liked_songs: bool = False):
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

        self.user = User(user_id=user_id)

        if liked_songs or playlist_id is not None or playlist_url is not None:
            self.select_playlist(
                liked_songs=liked_songs,
                playlist_id=playlist_id,
                playlist_url=playlist_url
            )

        else:
            logging.info('Class initiated without any playlist. To access any playlist related functions please use the select_playlist method.\nAll Profile related functions can still be used anyway you prefer')

    def needs_playlist(func): # type: ignore
        def wrapper(self, *args, **kwargs):
            if getattr(self, 'playlist', None) is None:
                raise ValueError('To access this function, you need to provide a playlist via the select_playlist method')

            return func(self, *args, **kwargs) # type: ignore

        return wrapper

    def select_playlist(
            self,
            liked_songs: bool = False,
            playlist_id: Union[str, None] = None,
            playlist_url: Union[str, None] = None,
        ) -> None:
        """Function to select a playlist to be mapped and be available on all the playlist related recommendation functions

        Args:
            playlist_id (str, optional): Playlist ID. Defaults to None.
            playlist_url (str, optional): Playlist Share URL (contains the ID, and it's easier to get). Defaults to None.
            liked_songs (bool, optional): Flag to use the user 'Liked songs' as the playlist. Defaults to False.
            prepare_favorites (bool, optional): Flag to prepare the deprecated functions for mid-term and short term favorites. Defaults to False.

        """
        if liked_songs:
            self.playlist = LikedSongs(user_id=self.user.user_id)

        elif playlist_id is not None:
            self.playlist = Playlist(user_id=self.user.user_id, playlist_id=playlist_id)

        elif playlist_url is not None:
            playlist_id = util.playlist_url_to_id(url=playlist_url)

            self.playlist = Playlist(user_id=self.user.user_id, playlist_id=playlist_id)

    def get_most_listened(self, time_range: str = 'long', number_of_songs: int = 50, build_playlist: bool = False) -> pd.DataFrame:
        """Function that creates the most-listened songs playlist for a given period of time in the users profile

        Args:
            time_range (str, optional): time range ('long_term', 'medium_term', 'short_term'). Defaults to 'long'.
            K (int, optional): Number of the most listened songs to return. Defaults to 50.

        Raises:
            ValueError: time range does not correspond to a valid time range ('long_term', 'medium_term', 'short_term')
            ValueError: Value for K must be between 1 and 1500


        Returns:
            pd.DataFrame: pandas DataFrame containing the top K songs in the time range
        """
        if time_range not in ['long_term', 'medium_term', 'short_term']:
            raise ValueError('time_range must be long_term, medium_term or short_term')

        if not (1 < number_of_songs <= 1500):
            raise ValueError(f'Value for K must be between 1 and 1500: {time_range} term most listened')

        return self.user.get_most_listened(
            time_range=time_range,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
        )

    def get_profile_recommendation(
            self,
            number_of_songs: int = 50,
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

        return self.user.get_profile_recommendation(
            time_range=time_range,
            main_criteria=main_criteria,
            save_with_date=save_with_date,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
        )

    def get_general_recommendation(
        self,
        number_of_songs: int = 50,
        build_playlist: bool = False,
        genres_info: Union['list[str]', None] = None,
        artists_info: Union['list[str]', None] = None,
        use_main_playlist_audio_features: bool = False,
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str], None]' = None,
    ) -> pd.DataFrame:
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
        if use_main_playlist_audio_features:
            audio_statistics = self.audio_features_statistics()
        else:
            audio_statistics = None

        return self.user.get_general_recommendation(
            genres_info=genres_info,
            tracks_info=tracks_info,
            artists_info=artists_info,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            audio_statistics=audio_statistics,
        )


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

    @needs_playlist # type: ignore
    def playlist_to_csv(self):
        """
        Function to convert playlist to CSV format
        Really useful if the package is being used in a .py file since it is not worth it to use it directly through web requests everytime even more when the playlist has not changed since last package usage
        """
        if getattr(self, 'playlist_url', None):
            playlist = self.playlist.get_dataframe()[
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

            playlist.to_csv(f'{self.playlist.playlist_name}.csv')

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
    def get_playlist(self) -> pd.DataFrame:
        """Function that returns the playlist as pandas DataFrame with the needed, human readable, columns

        Returns:
            pd.DataFrame: Playlist DataFrame
        """
        return self.__playlist[['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence']]

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
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

    @needs_playlist # type: ignore
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

    RequestHandler.get_auth()

    return SpotifyAPI(playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url, liked_songs=liked_songs)
