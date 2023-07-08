import pandas as pd

from functools import reduce
from abc import ABC, abstractmethod
from spotify_recommender_api.model.song import Song
from spotify_recommender_api.request_handler import RequestHandler

class BasePlaylist(ABC):
    playlist_id: str
    playlist_name: str
    songs: 'list[Song]'
    _genres: 'list[str]'
    _artists: 'list[str]'
    _dataframe: pd.DataFrame = pd.DataFrame([])


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

    def __init__(self, playlist_id: str) -> None:
        self.playlist_id = playlist_id

    def __post_init__(self) -> None:
        self.playlist_name = self.get_playlist_name(self.playlist_id)

        self._dataframe = self.retrieve_playlist_items()

        self.normalize_playlist()

    def retrieve_playlist_items(self):
        answer = input('Do you want to get the playlist data via CSV, which would have been saved previously, or read from spotify, which will take a few minutes depending on the playlist size (csv/web)? ')
        while answer.lower() not in ['csv', 'web']:  # , 'parquet'
            answer = input("Please select a valid response (csv/web): ")

        if answer.lower() == 'csv':
            return self.get_playlist_from_csv()

        return self.get_playlist_from_web()


    def normalize_playlist(self) -> None:
        self.index_genres()
        self.index_artists()

        self.add_indexed_columns()

        self.normalize_dtypes()

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


    def index_genres(self) -> None:
        genres_list = self._dataframe['genres'].to_list()

        playlist_genres = reduce(lambda all_genres, song_genres: all_genres + song_genres, genres_list, [])

        self._genres = list(set(playlist_genres))


    def index_artists(self) -> None:
        artists_list = self._dataframe['artists'].to_list()

        playlist_artists = reduce(lambda all_artists, song_artists: all_artists + song_artists, artists_list, [])

        self._artists = list(set(playlist_artists))


    def add_indexed_columns(self) -> None:
        self._dataframe['genres_indexed'] = self._dataframe.apply(lambda song: [int(genre in song['genres']) for genre in self._genres])
        self._dataframe['artists_indexed'] = self._dataframe.apply(lambda song: [int(artist in song['artists']) for artist in self._artists])


    def normalize_dtypes(self) -> None:
        self._dataframe['id'] = self._dataframe["id"].astype(str)
        self._dataframe['name'] = self._dataframe["name"].astype(str)
        self._dataframe['tempo'] = self._dataframe["tempo"].astype(float)
        self._dataframe['energy'] = self._dataframe["energy"].astype(float)
        self._dataframe['valence'] = self._dataframe["valence"].astype(float)
        self._dataframe['loudness'] = self._dataframe["loudness"].astype(float)
        self._dataframe['added_at'] = pd.to_datetime(self._dataframe["added_at"])
        self._dataframe['popularity'] = self._dataframe["popularity"].astype(int)
        self._dataframe['danceability'] = self._dataframe["danceability"].astype(float)
        self._dataframe['instrumentalness'] = self._dataframe["instrumentalness"].astype(float)


    def __retrieve_playlist_util_information(self):
        try:
            playlist_utils = pd.read_parquet(f'./.spotify-recommender-util/{self.playlist_name}.parquet')
        except FileNotFoundError as file_not_found_error:
            raise FileNotFoundError('The playlist with the specified ID does not exist in the CSV format, try again but selecting the "web" option, as the source for the playlist') from file_not_found_error

        artists, songs, all_genres = [
            eval(arr) if isinstance(arr, str) else arr
            for arr in [
                playlist_utils['artists'][0],
                playlist_utils['songs'][0],
                playlist_utils['all_genres'][0]
            ]
        ]

        return artists, songs, all_genres


    def retrieve_playlist_csv(self) -> pd.DataFrame:
        try:
            return pd.read_csv(f'{self.playlist_name}.csv')
        except FileNotFoundError as file_not_found_error:
            raise FileNotFoundError('The playlist with the specified ID does not exist in the CSV format, try again but selecting the "web" option, as the source for the playlist') from file_not_found_error


    def get_playlist_from_csv(self) -> pd.DataFrame:
        return self.retrieve_playlist_csv()


    def get_dataframe(self, indexes: bool = False) -> pd.DataFrame:
        playlist = self._dataframe.copy()

        if not indexes:
            playlist = playlist.drop(['genres_indexed', 'artists_indexed'])

        return playlist