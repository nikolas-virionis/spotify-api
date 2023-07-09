import pandas as pd

from functools import reduce

class PlaylistUtil:

    @staticmethod
    def _index_item(dataframe: pd.DataFrame, arg0: str) -> 'list[str]':
        items_list = dataframe[arg0].to_list()

        playlist_items = reduce(
            lambda all_items, song_items: all_items + song_items,
            items_list,
            [],
        )

        return list(set(playlist_items))


    @classmethod
    def _index_genres(cls, dataframe: pd.DataFrame) -> 'list[str]':
        return cls._index_item(dataframe=dataframe, arg0='genres')


    @classmethod
    def _index_artists(cls, dataframe: pd.DataFrame) -> 'list[str]':
        return cls._index_item(dataframe=dataframe, arg0='artists')


    @staticmethod
    def _add_indexed_columns(dataframe: pd.DataFrame, genres: 'list[str]', artists: 'list[str]') -> pd.DataFrame:
        dataframe['genres_indexed'] = dataframe.apply(lambda song: [int(genre in song['genres']) for genre in genres])
        dataframe['artists_indexed'] = dataframe.apply(lambda song: [int(artist in song['artists']) for artist in artists])

        return dataframe


    @staticmethod
    def _normalize_dtypes(dataframe: pd.DataFrame) -> pd.DataFrame:
        dataframe['id'] = dataframe["id"].astype(str)
        dataframe['name'] = dataframe["name"].astype(str)
        dataframe['tempo'] = dataframe["tempo"].astype(float)
        dataframe['energy'] = dataframe["energy"].astype(float)
        dataframe['valence'] = dataframe["valence"].astype(float)
        dataframe['loudness'] = dataframe["loudness"].astype(float)
        dataframe['added_at'] = pd.to_datetime(dataframe["added_at"])
        dataframe['popularity'] = dataframe["popularity"].astype(int)
        dataframe['danceability'] = dataframe["danceability"].astype(float)
        dataframe['instrumentalness'] = dataframe["instrumentalness"].astype(float)

        return dataframe
