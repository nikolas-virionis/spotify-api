import logging
import pandas as pd

from abc import ABC, abstractmethod
from spotify_recommender_api.song import Song
from spotify_recommender_api.playlist.util import PlaylistUtil
from spotify_recommender_api.playlist.features import PlaylistFeatures

class BasePlaylist(ABC):

    @staticmethod
    @abstractmethod
    def get_song_count(playlist_id: str) -> int:
        ...

    @staticmethod
    @abstractmethod
    def get_playlist_name(playlist_id: str) -> str:
        ...

    @abstractmethod
    def get_playlist_from_web(self) -> 'list[Song]':
        pass

    def __init__(self, user_id: str, retrieval_type: str, playlist_id: str = '') -> None:
        self.user_id = user_id
        self.playlist_id = playlist_id
        self.playlist_name = self.get_playlist_name(playlist_id)

        self._dataframe = pd.DataFrame(self._retrieve_playlist_items(retrieval_type=retrieval_type))

        self._normalize_playlist()

        PlaylistFeatures.base_playlist_name = self.playlist_name
        PlaylistFeatures.user_id = self.user_id


    def _retrieve_playlist_items(self, retrieval_type: str) -> 'list[Song]':
        """_summary_

        Args:
            retrieval_type (str): The playlist items retrieval type. Has to be either "csv" or "web".

        Raises:
            FileNotFoundError: In case of the retrieval_type being CSV and there is no CSV file available, the error is raised

        Returns:
            list[Song]: List of songs in the playlist mapping
        """
        if retrieval_type.lower() not in {'csv', 'web'}:
            raise ValueError('The playlist items retrieval_type has to be either "csv" or "web"')

        if retrieval_type.lower() == 'csv':
            return self.get_playlist_from_csv()

        return self.get_playlist_from_web()


    def _normalize_playlist(self) -> None:
        self._genres = PlaylistUtil._index_genres(dataframe=self._dataframe)
        self._artists = PlaylistUtil._index_artists(dataframe=self._dataframe)

        self._dataframe = PlaylistUtil._add_indexed_columns(
            genres=self._genres,
            artists=self._artists,
            dataframe=self._dataframe,
        )

        self._dataframe = PlaylistUtil._normalize_dtypes(dataframe=self._dataframe)

    def _retrieve_playlist_csv(self) -> pd.DataFrame:
        try:
            return pd.read_csv(f'{self.playlist_name}.csv', index_col=[0])
        except FileNotFoundError as file_not_found_error:
            raise FileNotFoundError('The playlist with the specified ID does not exist in the CSV format, try again but selecting the "web" option, as the source for the playlist') from file_not_found_error

    def get_playlist_from_csv(self) -> pd.DataFrame:
        return self._retrieve_playlist_csv()


    def get_dataframe(self, indexes: bool = False) -> pd.DataFrame:
        playlist = self._dataframe.copy()

        if not indexes:
            playlist = playlist.drop(['genres_indexed', 'artists_indexed'], axis=1)

        return playlist


    def get_recommendations_for_song(
        self,
        song_name: str,
        artist_name: str,
        number_of_songs: int,
        with_distance: bool = False,
        build_playlist: bool = False,
        print_base_caracteristics: bool = False,
        _auto_artist: bool = False
    ) -> pd.DataFrame:
        """Playlist which centralises the actions for a recommendation made for a given song

        Note
            The build_playlist option when set to True will change the user's library


        Args:
            number_of_songs (int): desired number number_of_songs of neighbors to be returned
            song (str): The desired song name
            generate_csv (bool, optional): Whether to generate a CSV file containing the recommended playlist. Defaults to False.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            generate_parquet (bool, optional): Whether to generate a parquet file containing the recommended playlist. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. Defaults to False.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500

        Returns:
            pd.DataFrame: Pandas DataFrame containing the song recommendations
        """

        dataframe = PlaylistFeatures.get_recommendations_for_song(
            song_name=song_name,
            artist_name=artist_name,
            _auto_artist=_auto_artist,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            dataframe=self._dataframe.copy(),
            print_base_caracteristics=print_base_caracteristics,
        )

        if dataframe is None:
            return None

        if not with_distance:
            dataframe = dataframe.drop('distance', axis=1)

        return dataframe


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

        return PlaylistFeatures.get_playlist_trending_genres(
            plot_top=plot_top,
            time_range=time_range,
            dataframe=self._dataframe.copy(),
        )


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

        return PlaylistFeatures.get_playlist_trending_artists(
            plot_top=plot_top,
            time_range=time_range,
            dataframe=self._dataframe.copy(),
        )

    def artist_only_playlist(
        self,
        artist_name: str,
        number_of_songs: int = 50,
        build_playlist: bool = False,
        ensure_all_artist_songs: bool = True
    ) -> pd.DataFrame:  # sourcery skip: extract-method
        """Function that generates DataFrame containing only a specific artist songs, with the possibility of completing it with the closest songs to that artist

        Args:
            artist_name (str): The name of the artist
            number_of_songs (int, optional): Maximum number of songs. Defaults to 50.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since it does not obey any actual unit, it is just a mathematical value to determine the closet songs. ONLY TAKES EFFECT IF complete_with_similar == True AND number_of_songs > NUMBER_OF_SONGS_WITH_THAT_ARTIST. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            ensure_all_artist_songs (bool, optional): Whether to ensure that all artist songs are in the playlist, regardless of the number_of_songs number specified. Defaults to True
            complete_with_similar (bool, optional): Flag to complete the list of songs with songs that are similar to that artist, until the number_of_songs number is reached. Only applies if number_of_songs is greater than the number of songs by that artist in the playlist. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. ONLY TAKES EFFECT IF complete_with_similar == True AND number_of_songs > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """
        return PlaylistFeatures.artist_only_playlist(
            user_id=self.user_id,
            artist_name=artist_name,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            dataframe=self._dataframe.copy(),
            base_playlist_name=self.playlist_name,
            ensure_all_artist_songs=ensure_all_artist_songs
        )

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
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since it does not obey any actual unit, it is just a mathematical value to determine the closet songs. ONLY TAKES EFFECT IF complete_with_similar == True AND number_of_songs > NUMBER_OF_SONGS_WITH_THAT_ARTIST. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            ensure_all_artist_songs (bool, optional): Whether to ensure that all artist songs are in the playlist, regardless of the number_of_songs number specified. Defaults to True
            complete_with_similar (bool, optional): Flag to complete the list of songs with songs that are similar to that artist, until the number_of_songs number is reached. Only applies if number_of_songs is greater than the number of songs by that artist in the playlist. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. ONLY TAKES EFFECT IF complete_with_similar == True AND number_of_songs > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """

        return PlaylistFeatures.artist_and_related_playlist(
            user_id=self.user_id,
            all_genres=self._genres,
            artist_name=artist_name,
            all_artists=self._artists,
            with_distance=with_distance,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            dataframe=self._dataframe.copy(),
            base_playlist_name=self.playlist_name,
            print_base_caracteristics=print_base_caracteristics
        )


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
        return PlaylistFeatures.audio_features_extraordinary_songs(dataframe=self._dataframe.copy())


    def audio_features_statistics(self) -> 'dict[str, float]':
        """FUnctions that returns the statistics (max, min and mean) for the audio features within the playlist

        Returns:
            dict[str, float]: The dictionary with the statistics
        """
        return PlaylistFeatures.audio_features_statistics(dataframe=self._dataframe.copy())


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
            ValueError: 'mixed', 'artists', 'tracks', 'genres'

        Returns:
            pd.DataFrame: Recommendations playlist
        """
        return PlaylistFeatures.get_playlist_recommendation(
            user_id=self.user_id,
            time_range=time_range,
            main_criteria=main_criteria,
            save_with_date=save_with_date,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            dataframe=self._dataframe.copy(),
            base_playlist_name=self.playlist_name,
        )


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
        return PlaylistFeatures.get_songs_by_mood(
            mood=mood,
            user_id=self.user_id,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            dataframe=self._dataframe.copy(),
            base_playlist_name=self.playlist_name,
            exclude_mostly_instrumental=exclude_mostly_instrumental
        )


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
        return PlaylistFeatures.playlist_songs_based_on_most_listened_tracks(
            user_id=self.user_id,
            time_range=time_range,
            all_genres=self._genres,
            all_artists=self._artists,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            dataframe=self._dataframe.copy(),
            base_playlist_name=self.playlist_name,
        )

