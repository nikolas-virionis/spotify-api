import logging
import warnings
import pandas as pd
import spotify_recommender_api.util as util

from typing import Union, Any, Callable
from spotify_recommender_api.user import User
from spotify_recommender_api.playlist.playlist import Playlist
from spotify_recommender_api.error import NoPlaylistProvidedError
from spotify_recommender_api.playlist.liked_songs import LikedSongs
from spotify_recommender_api.requests.request_handler import RequestHandler

warnings.filterwarnings('error')


class SpotifyAPI:
    """Spotify API is the Class that provides access to the playlists recommendations"""

    def __init__(self, user_id: str, playlist_id: Union[str, None] = None, playlist_url: Union[str, None] = None, liked_songs: bool = False):
        """Spotify API is the Class that provides access to the playlists recommendations

        Note:
            It will trigger most of the API functions and can take a good while to complete if the playlist is specified, and the "web" option selected to retrieve the playlist items


        Args:
            user_id (str): The user ID, visible in the Spotify profile account settings
            playlist_id (str, optional): The playlist ID hash in Spotify. Defaults to None.
            playlist_url (str, optional): The url used while sharing the playlist. Defaults to None.
            liked_songs (bool, optional): Whether to use the User's Liked Songs as the base playlist, Defaults to False.

        """

        self.user = User(user_id=user_id)

        if liked_songs or playlist_id is not None or playlist_url is not None:
            self.select_playlist(
                liked_songs=liked_songs,
                playlist_id=playlist_id,
                playlist_url=playlist_url
            )

        else:
            logging.info('Class initiated without any playlist. To access any playlist-related functions please use the select_playlist method.\nAll Profile related functions can still be used in any way you prefer')

        logging.info('After version 5.0.0 there has been a full refactoring of the package, so any problems that you may encounter, submit an issue at: https://github.com/nikolas-virionis/spotify-api/issues')

    def needs_playlist(func: Callable[..., Any]) -> Callable[..., Any]: # type: ignore
        """Decorator to check if a playlist is provided before accessing a function.

        Args:
            func (Callable[..., Any]): The function to be decorated.

        Returns:
            Callable[..., Any]: The decorated function.
        """
        def wrapper(self, *args, **kwargs):
            if getattr(self, 'playlist', None) is None:
                raise NoPlaylistProvidedError('To access this function, you need to provide a playlist via the select_playlist method')

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

        """
        if liked_songs:
            self.playlist = LikedSongs(user_id=self.user.user_id)

        elif playlist_id is not None:
            self.playlist = Playlist(user_id=self.user.user_id, playlist_id=playlist_id)

        elif playlist_url is not None:
            playlist_id = util.playlist_url_to_id(url=playlist_url)

            self.playlist = Playlist(user_id=self.user.user_id, playlist_id=playlist_id)

    def get_most_listened(self, time_range: str = 'long_term', number_of_songs: int = 50, build_playlist: bool = False) -> pd.DataFrame:
        """Function that creates the most-listened songs playlist for a given period of time in the users profile

        Args:
            time_range (str, optional): time range ('long_term', 'medium_term', 'short_term'). Defaults to 'long'.
            number_of_songs (int, optional): Number of the most listened songs to return. Defaults to 50.
            build_playlist (bool, optional): Whether to create, or update, a playlist in the user's library. Defaults to False.

        Raises:
            ValueError: time range does not correspond to a valid time range ('long_term', 'medium_term', 'short_term')
            ValueError: Value for number_of_songs must be between 1 and 1500


        Returns:
            pd.DataFrame: pandas DataFrame containing the top number_of_songs songs in the time range
        """
        if time_range not in ['long_term', 'medium_term', 'short_term']:
            raise ValueError('time_range must be long_term, medium_term or short_term')

        if not (1 <= number_of_songs <= 1500):
            raise ValueError(f'Value for number_of_songs must be between 1 and 1500: {time_range} term most listened')

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
        ) -> pd.DataFrame:
        """Builds a Profile based recommendation

        Args:
            number_of_songs (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            main_criteria (str, optional): Main criteria for the recommendations playlist. Can be one of the following: 'mixed', 'artists', 'tracks', 'genres'. Defaults to 'mixed'.
            save_with_date (bool, optional): Flag to save the recommendations playlist as a Point in Time Snapshot. Defaults to False.
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.
            time_range (str, optional): The time range to get the profile most listened information from. Can be one of the following: 'short_term', 'medium_term', 'long_term'. Defaults to 'short_term'

        Raises:
            ValueError: If number_of_songs is not between 1 and 100.
            ValueError: If main_criteria is not one of 'mixed', 'artists', 'tracks', 'genres'.
            ValueError: If time_range is not one of 'short_term', 'medium_term', 'long_term'.

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
            number_of_songs (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            genres_info (list[str], optional): list of the genre names to be used in the recommendation. Defaults to [].
            artists_info (list[str], optional): list of the artist names to be used in the recommendation. Defaults to [].
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.
            use_main_playlist_audio_features (bool, optional): Flag to use the audio features of the main playlist to target better recommendations. Defaults to False.
            tracks_info (list[str] | list[tuple[str]] | list[list[str]] | dict[str, str]], optional): List of the song names to be used in the recommendations. They can be only the song names, but since there are a lot of songs with the same name i recommend using also the artist name in a key-value format using either a tuple, or list, or dict. Examples below. Defaults to [].

        Raises:
            ValueError: number_of_songs must be between 1 and 100
            ValueError: At least one of the three args must be provided: genres_info, artists_info, tracks_info
            ValueError: The sum of the number of items in each of the three args mustn't exceed 5
            ValueError: The argument tracks_info must be an instance of one of the following 4 types: list[str], list[tuple[str]], list[list[str]], dict[str, str]

        Returns:
            pd.DataFrame: Recommendations playlist

        ## Examples of tracks_info
        >>> api.get_general_recommendation(tracks_info={'song': 'artist', 'song': 'artist'})
        # or
        >>> api.get_general_recommendation(tracks_info=[('song', 'artist'), ('song', 'artist')])
        # or
        >>> api.get_general_recommendation(tracks_info=[['song', 'artist'], ['song', 'artist']])
        # or, but not recommended
        >>> api.get_general_recommendation(tracks_info=['song', 'song'])
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

    @needs_playlist
    def playlist_to_csv(self):
        """
        Function to convert playlist to CSV format. \n
        Really useful if the package is being used in a .py file since it is not worth it to use it directly through web requests everytime even more when the playlist has not changed since last package usage, making it possible to store it for easier and quicker access
        """

        playlist = self.get_playlist()

        playlist.to_csv(f'{self.playlist.playlist_name}.csv')

    @needs_playlist
    def get_recommendations_for_song(
        self,
        song_name: str,
        artist_name: str,
        number_of_songs: int = 50,
        with_distance: bool = False,
        build_playlist: bool = False,
        print_base_caracteristics: bool = False
    ) -> pd.DataFrame:
        """Playlist which centralises the actions for a recommendation made for a given song

        Note
            The build_playlist option when set to True will change the user's library


        Args:
            song_name (str): The desired song name
            artist_name (str): The desired song's artist name
            number_of_songs (int): desired number number_of_songs of neighbors to be returned
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. Defaults to False.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500

        Returns:
            pd.DataFrame: Pandas DataFrame containing the song recommendations
        """
        return self.playlist.get_recommendations_for_song(
            song_name=song_name,
            artist_name=artist_name,
            with_distance=with_distance,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            print_base_caracteristics=print_base_caracteristics
        )

    @needs_playlist
    def get_playlist(self) -> pd.DataFrame:
        """Function that returns the playlist as pandas DataFrame with the needed, human readable, columns

        Returns:
            pd.DataFrame: Playlist DataFrame
        """
        return self.playlist.get_dataframe().copy()[
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

    @needs_playlist
    def get_playlist_trending_genres(self, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> pd.DataFrame:
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

        return self.playlist.get_playlist_trending_genres(
            plot_top=plot_top,
            time_range=time_range,
        )

    @needs_playlist
    def get_playlist_trending_artists(self, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> pd.DataFrame:
        """Calculates the amount of times each artist was spotted in the playlist, and can plot a bar chart to represent this information

        Args:
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            plot_top(int|bool , optional): the number of top genres to be plotted. No chart will be plotted if set to False. Defaults to False.

        Raises:
            ValueError: If the time_range parameter is not valid the error is raised.

        Returns:
            pd.DataFrame: The dictionary that contains how many times each artist was spotted in the playlist in the given time range.
        """

        return self.playlist.get_playlist_trending_artists(
            plot_top=plot_top,
            time_range=time_range,
        )

    @needs_playlist
    def artist_only_playlist(
        self,
        artist_name: str,
        number_of_songs: int = 50,
        build_playlist: bool = False,
        ensure_all_artist_songs: bool = True
    ) -> pd.DataFrame:
        """Function that generates DataFrame containing only a specific artist songs, with the possibility of completing it with the closest songs to that artist

        Args:
            artist_name (str): The name of the artist
            number_of_songs (int, optional): Maximum number of songs. Defaults to 50.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since it does not obey any actual unit, it is just a mathematical value to determine the closet songs.  Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            ensure_all_artist_songs (bool, optional): Whether to ensure that all artist songs are in the playlist, regardless of the number_of_songs number specified. Defaults to True
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. ONLY TAKES EFFECT IF complete_with_similar == True AND number_of_songs > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """
        return self.playlist.artist_only_playlist(
            artist_name=artist_name,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            ensure_all_artist_songs=ensure_all_artist_songs
        )

    @needs_playlist
    def artist_and_related_playlist(
        self,
        artist_name: str,
        number_of_songs: int = 50,
        with_distance: bool = False,
        build_playlist: bool = False,
        print_base_caracteristics: bool = False,
    ) -> pd.DataFrame:
        """Function that generates DataFrame containing only a specific artist songs, with the possibility of completing it with the closest songs to that artist

        Args:
            artist_name (str): The name of the artist
            number_of_songs (int, optional): Maximum number of songs. Defaults to 50.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since it does not obey any actual unit, it is just a mathematical value to determine the closet songs. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. ONLY TAKES EFFECT IF complete_with_similar == True AND number_of_songs > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """
        return self.playlist.artist_and_related_playlist(
            artist_name=artist_name,
            with_distance=with_distance,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            print_base_caracteristics=print_base_caracteristics
        )

    @needs_playlist
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
        return self.playlist.audio_features_extraordinary_songs()

    @needs_playlist
    def audio_features_statistics(self) -> 'dict[str, float]':
        """Functions that returns the statistics (max, min and mean) for the audio features within the playlist

        Returns:
            dict[str, float]: The dictionary with the statistics
        """
        return self.playlist.audio_features_statistics()

    @needs_playlist
    def get_playlist_recommendation(
        self,
        number_of_songs: int = 50,
        time_range: str = 'all_time',
        main_criteria: str = 'mixed',
        save_with_date: bool = False,
        build_playlist: bool = False,
    ) -> pd.DataFrame:
        """Builds a playlist based recommendation

        Args:
            number_of_songs (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            main_criteria (str, optional): Main criteria for the recommendations playlist. Can be one of the following: 'mixed', 'artists', 'tracks', 'genres'. Defaults to 'mixed'.
            save_with_date (bool, optional): Flag to save the recommendations playlist as a Point in Time Snapshot. Defaults to False.
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.

        Raises:
            ValueError: number_of_songs must be between 1 and 100
            ValueError: main_criteria has to be on of the following: 'mixed', 'artists', 'tracks', 'genres'

        Returns:
            pd.DataFrame: Recommendations playlist
        """

        return self.playlist.get_playlist_recommendation(
            time_range=time_range,
            main_criteria=main_criteria,
            save_with_date=save_with_date,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
        )

    @needs_playlist
    def get_songs_by_mood(
            self,
            mood: str,
            number_of_songs: int = 50,
            build_playlist: bool = False,
            exclude_mostly_instrumental: bool = False
        ) -> pd.DataFrame:
        """Function to create playlists based on the general mood of a song

        Args:
            mood (str): The mood of the song. Can be 'happy', 'sad' or 'calm'
            number_of_songs (int, optional): Number of songs. Defaults to 50.
            build_playlist (bool, optional): Flag to create the playlist in the user's library. Defaults to False.
            exclude_mostly_instrumental (bool, optional): Flag to exclude the songs which are 80% or more instrumental. Defaults to False.

        Raises:
            ValueError: If the mood is not one of the valid options the error is raised

        Returns:
            pd.DataFrame: A DataFrame containing the new playlist
        """
        return self.playlist.get_songs_by_mood(
            mood=mood,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            exclude_mostly_instrumental=exclude_mostly_instrumental
        )

    @needs_playlist
    def playlist_songs_based_on_most_listened_tracks(
            self,
            number_of_songs: int = 50,
            build_playlist: bool = False,
            time_range: str = 'short_term',
        ) -> pd.DataFrame:
        """Function to create a playlist with songs from the base playlist that are the closest to the user's most listened songs

        Args:
            number_of_songs (int, optional): Number of songs. Defaults to 50.
            build_playlist (bool, optional): Flag to create the playlist in the user's library. Defaults to False.
            time_range (str, optional): String to identify which is the time range, could be one of the following: {'short_term', 'medium_term', 'long_term'}. Defaults to 'short_term'.

        Raises:
            ValueError: time_range needs to be one of the following: 'short_term', 'medium_term', 'long_term'

        Returns:
            pd.DataFrame: DataFrame that contains the information of all songs in the new playlist
        """
        return self.playlist.playlist_songs_based_on_most_listened_tracks(
            time_range=time_range,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
        )

    def update_all_generated_playlists(
            self, *,
            playlist_types_to_update: Union['list[str]', None] = None,
            playlist_types_not_to_update: Union['list[str]', None] = None
        ) -> None:
        """Update all package generated playlists in batch

        Arguments:
            playlist_types_to_update (list[str], optional, keyword-argument): List of playlist types to update. For example, if you only want to update song-related playlists use this argument as ['song-related']. Defaults to all == ['most-listened-tracks', 'song-related', 'artist-mix', 'artist-full', 'playlist-recommendation', 'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation', 'mood', 'most-listened-recommendation'].
            playlist_types_not_to_update (list[str], optional, keyword-argument): List of playlist types not to update. For example, if you want to update all playlists but song-related playlists use this argument as ['song-related']. it can be used alongside with the playlist_types_to_update but it can become confusing or redundant. Defaults to none == [].
        """
        self.user.update_all_generated_playlists(
            base_playlist=getattr(self, 'playlist', None),
            playlist_types_to_update=playlist_types_to_update,
            playlist_types_not_to_update=playlist_types_not_to_update,
        )

def start_api(
    user_id: str, *,
    log_level: str = 'INFO',
    liked_songs: bool = False,
    playlist_url: Union[str, None] = None,
    playlist_id: Union[str, None] = None,
) -> SpotifyAPI:
    """Function that prepares for and initializes the API

    Note:
        Internet Connection is required

    Args:
        user_id(str): the id of user, present in the user account profile

    Keyword Arguments:
        playlist_url (str, optional, keyword-argument only): the url for the playlist, which is visible when trying to share it. Defaults to False.
        playlist_id (str, optional, keyword-argument only): the id of the playlist, an unique big hash which identifies the playlist. Defaults to False.
        liked_songs (bool, optional, keyword-argument only): A flag to identify if the playlist to be mapped is the Liked Songs. Defaults to False.
        log_level (str, optional, keyword-argument only): The log level, of the logging library, to be used. Defaults to INFO

    Raises:
        ValueError: when passing the arguments, there should be only one or none filled between playlist_url, playlist_id and liked_songs

    Returns:
        SpotifyAPI: The instance of the SpotifyAPI class
    """
    if log_level.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        raise ValueError("log_level must be one of the following: 'DEBUG', 'INFO', 'WARNING', 'ERROR'")

    logging.basicConfig(
        level=log_level.upper(),
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s',
    )

    if (playlist_url is not None or playlist_id is not None) and liked_songs or (playlist_url is not None and playlist_id is not None):
        raise ValueError('It is necessary to specify only one or none of the following parameters: playlist_id or playlist_url or liked_songs')

    logging.info('Retrieving Authentication token')

    RequestHandler.get_auth()
    logging.debug('Authentication complete')

    return SpotifyAPI(playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url, liked_songs=liked_songs)
