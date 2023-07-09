import pandas as pd
import spotify_recommender_api.util as util

from typing import Union, Any
from spotify_recommender_api.core.library import Library
from spotify_recommender_api.model.song import Song
from spotify_recommender_api.core.knn_algorithm import KNNAlgorithm


class PlaylistFeatures:
    user_id: str
    base_playlist_name: str


    @classmethod
    def get_recommendations_for_song(
        cls,
        song_name: str,
        artist_name: str,
        number_of_songs: int,
        dataframe: pd.DataFrame,
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
        if not (1 < number_of_songs <= 1500):
            raise ValueError(f'Value for number_of_songs must be between 1 and 1500 on creation of recommendation for the song {song_name} {f"by {artist_name}" if artist_name is not None else ""}')

        song = cls._get_song(song_name=song_name, artist_name=artist_name, dataframe=dataframe)

        df = cls.__get_recommendations(
            song=song,
            dataframe=dataframe,
            recommendation_type='song',
            number_of_songs=number_of_songs
        )

        if print_base_caracteristics:
            util.print_base_caracteristics(
                song.id,
                song.name,
                song.genres,
                song.artists,
                song.popularity,
                song.danceability,
                song.loudness,
                song.energy,
                song.instrumentalness,
                song.tempo,
                song.valence
            )

        ids = df['id'].to_list()

        if build_playlist:
            Library.write_playlist(
                ids=ids,
                user_id=cls.user_id,
                playlist_type='song',
                base_playlist_name=cls.base_playlist_name
            )

        return df

    @classmethod
    def __get_recommendations(cls, song: Song, recommendation_type: str, dataframe: pd.DataFrame, number_of_songs: int = 50) -> pd.DataFrame:
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

        return KNNAlgorithm.get_neighbors(
            song=song,
            dataframe=dataframe,
            number_of_songs=number_of_songs,
            recommendation_type=recommendation_type,
        )

    @classmethod
    def _get_song(cls, dataframe: pd.DataFrame, song_name: str, artist_name: Union[str, None] = None) -> Song:
        """Function that returns the index of a given song in the list of songs

        Args:
            song (str): song name

        Raises:
            ValueError: Playlist does not contain the song

        Returns:
            Song: The song
        """
        query = 'name == @song_name'

        if artist_name is not None:
            query += ' AND @artist_name in artists'

        dataframe = dataframe.copy().query(query)

        song_dict = {**dataframe.to_dict('records')[0]}

        return Song(**song_dict) # type: ignore
