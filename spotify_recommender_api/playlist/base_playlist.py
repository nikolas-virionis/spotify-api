import pandas as pd

from abc import ABC, abstractmethod
from spotify_recommender_api.model.song import Song
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
    def get_playlist_from_web(self) -> pd.DataFrame:
        pass

    def __init__(self, user_id: str, playlist_id: str = '') -> None:
        self.user_id = user_id
        self.playlist_id = playlist_id

    def __post_init__(self) -> None:
        self.playlist_name = self.get_playlist_name(self.playlist_id)

        self._dataframe = self._retrieve_playlist_items()

        self._normalize_playlist()

        PlaylistFeatures.base_playlist_name = self.playlist_name
        PlaylistFeatures.user_id = self.user_id

    def _retrieve_playlist_items(self) -> pd.DataFrame:
        answer = input('Do you want to get the playlist data via CSV, which would have been saved previously, or read from spotify, which will take a few minutes depending on the playlist size (csv/web)? ')
        while answer.lower() not in ['csv', 'web']:  # , 'parquet'
            answer = input("Please select a valid response (csv/web): ")

        if answer.lower() == 'csv':
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

        self.songs = [
            Song(
                id=song['id'],
                name=song['name'],
                tempo=song['tempo'],
                energy=song['energy'],
                genres=song['genres'],
                valence=song['valence'],
                artists=song['artists'],
                added_at=song['added_at'],
                loudness=song['loudness'],
                popularity=song['popularity'],
                danceability=song['danceability'],
                genres_indexed=song['genres_indexed'],
                artists_indexed=song['artists_indexed'],
                instrumentalness=song['instrumentalness'],
            )
            for song in self._dataframe.to_dict('records')
        ]

    def _retrieve_playlist_csv(self) -> pd.DataFrame:
        try:
            return pd.read_csv(f'{self.playlist_name}.csv')
        except FileNotFoundError as file_not_found_error:
            raise FileNotFoundError('The playlist with the specified ID does not exist in the CSV format, try again but selecting the "web" option, as the source for the playlist') from file_not_found_error


    def get_playlist_from_csv(self) -> pd.DataFrame:
        return self._retrieve_playlist_csv()


    def get_dataframe(self, indexes: bool = False) -> pd.DataFrame:
        playlist = self._dataframe.copy()

        if not indexes:
            playlist = playlist.drop(['genres_indexed', 'artists_indexed'])

        return playlist


    def get_recommendations_for_song(
        self,
        song_name: str,
        artist_name: str,
        with_distance: bool,
        number_of_songs: int,
        build_playlist: bool = False,
        print_base_caracteristics: bool = False
    ) -> pd.DataFrame:
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

        dataframe = PlaylistFeatures.get_recommendations_for_song(
            song_name=song_name,
            artist_name=artist_name,
            dataframe=self._dataframe,
            build_playlist=build_playlist,
            number_of_songs=number_of_songs,
            print_base_caracteristics=print_base_caracteristics
        )

        if not with_distance:
            dataframe = dataframe.drop('distance')

        return dataframe
