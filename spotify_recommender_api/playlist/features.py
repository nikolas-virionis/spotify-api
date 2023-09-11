import logging
import datetime
import pandas as pd
import spotify_recommender_api.util as util
import spotify_recommender_api.visualization as visualization

from typing import Any
from dateutil.tz import tz
from functools import reduce
from spotify_recommender_api.song import Song
from spotify_recommender_api.song.util import SongUtil
from spotify_recommender_api.core.library import Library
from spotify_recommender_api.error import EmptyResultError
from spotify_recommender_api.core.knn_algorithm import KNNAlgorithm
from spotify_recommender_api.requests.api_handler import UserHandler
from spotify_recommender_api.requests.request_handler import RequestHandler, BASE_URL



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
        print_base_caracteristics: bool = False,
        _auto_artist: bool = False,
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
        if not (1 <= number_of_songs <= 1500):
            raise ValueError(f'Value for number_of_songs must be between 1 and 1500 on creation of recommendation for the song {song_name} by {artist_name}')

        song = cls._get_song(song_name=song_name, artist_name=artist_name, dataframe=dataframe, _auto_artist=_auto_artist)

        if song is None:
            return None

        if _auto_artist:
            artist_name = eval(song.artists)[0]

        df = cls._get_recommendations(
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

        ids = [song.id, *df['id'].to_list()]

        if build_playlist:
            Library.write_playlist(
                ids=ids,
                user_id=cls.user_id,
                song_name=song_name,
                playlist_type='song',
                artist_name=artist_name,
                base_playlist_name=cls.base_playlist_name
            )

        return df

    @classmethod
    def _get_recommendations(cls, song: Song, recommendation_type: str, dataframe: pd.DataFrame, number_of_songs: int = 50) -> pd.DataFrame:
        """General purpose function to get recommendations for any type supported by the package

        Args:
            info (Any): the changed song_dict list if the type is short or medium or else it is the name of the song to get recommendations from
            number_of_songs (int, optional): desired number of neighbors to be returned. Defaults to 51.
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
    def _get_song(cls, dataframe: pd.DataFrame, song_name: str, artist_name: str, _auto_artist: bool = False) -> Song:
        """Function that returns the index of a given song in the list of songs

        Args:
            song (str): song name

        Raises:
            ValueError: Playlist does not contain the song

        Returns:
            Song: The song
        """
        dataframe = dataframe.copy()

        dataframe = dataframe.query('name == @song_name')

        if not _auto_artist:
            dataframe = dataframe[dataframe['artists'].apply(lambda artists: artist_name in artists)]

        if dataframe.empty:
            logging.warning(f'Playlist has no song named {song_name} {"" if _auto_artist else f"by {artist_name}"}')
            return None

        song_dict = {**dataframe.to_dict('records')[0]}

        return Song(**song_dict) # type: ignore

    @classmethod
    def get_playlist_trending_genres(cls, dataframe: pd.DataFrame, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> pd.DataFrame:
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
        added_at_begin = cls._get_datetime_by_time_range(time_range)

        playlist = cls._filter_playlist_by_time(dataframe, added_at_begin)

        if playlist.empty:
            logging.warning(f"No songs added to the playlist in the time range {time_range} ")
            raise EmptyResultError("No songs added to the playlist in the time range")

        genres = cls._extract_items_from_playlist(playlist, 'genres')

        genres_dict = cls._count_items(genres)

        genres_dict = cls._sort_items_by_count(genres_dict)

        genres_dict = cls._calculate_item_percentage(genres_dict)

        df = cls._create_dataframe(genres_dict)

        if plot_top:
            cls._plot_bar_chart(df, plot_top, time_range, 'genres')

        return df

    @classmethod
    def get_playlist_trending_artists(cls, dataframe: pd.DataFrame, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> pd.DataFrame:
        """Calculates the amount of times each artist was spotted in the playlist, and can plot a bar chart to represent this information

        Args:
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            plot_top(int|bool , optional): the number of top genres to be plotted. No chart will be plotted if set to False. Defaults to False.

        Raises:
            ValueError: If the time_range parameter is not valid the error is raised.

        Returns:
            pd.DataFrame: The dictionary that contains how many times each artist was spotted in the playlist in the given time range.
        """
        added_at_begin = cls._get_datetime_by_time_range(time_range)

        playlist = cls._filter_playlist_by_time(dataframe, added_at_begin)

        if playlist.empty:
            logging.warning(f"No songs added to the playlist in the time range {time_range} ")
            raise EmptyResultError("No songs added to the playlist in the time range")

        artists = cls._extract_items_from_playlist(playlist, 'artists')

        artists_dict = cls._count_items(artists)

        artists_dict = cls._sort_items_by_count(artists_dict)

        artists_dict = cls._calculate_item_percentage(artists_dict)

        df = cls._create_dataframe(artists_dict)

        if plot_top:
            cls._plot_bar_chart(df, plot_top, time_range, 'artists')

        return df


    @staticmethod
    def _get_datetime_by_time_range(time_range: str) -> datetime.datetime:
        valid_time_ranges = ['all_time', 'month', 'trimester', 'semester', 'year']
        if time_range not in valid_time_ranges:
            raise ValueError(f'time_range must be one of the following: {", ".join(valid_time_ranges)}')

        return util.get_datetime_by_time_range(time_range=time_range)

    @staticmethod
    def _filter_playlist_by_time(dataframe: pd.DataFrame, added_at_begin: datetime.datetime) -> pd.DataFrame:
        added_at_begin = pd.to_datetime(added_at_begin.astimezone(tz.tzutc()))
        try:
            dataframe['added_at'] = pd.to_datetime(dataframe['added_at'], errors='coerce').dt.tz_localize(tz.tzutc())
        except Exception:
            dataframe['added_at'] = pd.to_datetime(dataframe['added_at'], errors='coerce').dt.tz_convert(tz.tzutc())

        return dataframe[dataframe['added_at'] >= added_at_begin]
        # return dataframe.query('added_at > @added_at_begin')

    @staticmethod
    def _extract_items_from_playlist(playlist: pd.DataFrame, item_key: str) -> list:
        return list(reduce(lambda x, y: x + eval(str(y)), playlist[item_key], []))

    @staticmethod
    def _count_items(items: list) -> dict:
        return {**dict(reduce(lambda x, y: util.list_to_count_dict(dictionary=x, item=y), items, {})), 'total': len(items)}

    @staticmethod
    def _sort_items_by_count(items_dict: dict) -> dict:
        return dict(sorted(items_dict.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def _calculate_item_percentage(items_dict: dict) -> dict:
        return util.value_dict_to_value_and_percentage_dict(dictionary=items_dict)

    @staticmethod
    def _create_dataframe(items_dict: dict) -> pd.DataFrame:
        dictionary = {'name': [], 'number of songs': [], 'rate': []}

        for key, value in items_dict.items():
            dictionary['name'].append(key)
            dictionary['number of songs'].append(value['value'])
            dictionary['rate'].append(value['percentage'])

        return pd.DataFrame(data=dictionary, columns=['name', 'number of songs', 'rate'])

    @staticmethod
    def _plot_bar_chart(df: pd.DataFrame, plot_top: int, time_range: str, item_key: str):
        if plot_top > 30:
            raise ValueError('plot_top must be either an int smaller than 30 or False')

        visualization.plot_bar_chart(
            df=df,
            top=plot_top,
            plot_max=reduce(lambda x, y: x + y, df['rate'][1:4], 0) >= 0.50,
            chart_title=f"Most present {item_key} in the playlist {f'in the last {time_range}' if time_range != 'all_time' else ''}",
        )

    @classmethod
    def artist_only_playlist(
        cls,
        user_id: str,
        artist_name: str,
        dataframe: pd.DataFrame,
        base_playlist_name: str,
        number_of_songs: int = 50,
        build_playlist: bool = False,
        ensure_all_artist_songs: bool = True
    ) -> pd.DataFrame:
        """Function that generates DataFrame containing only a specific artist songs, with the possibility of completing it with the closest songs to that artist

        Args:
            artist_name (str): The name of the artist
            number_of_songs (int, optional): Maximum number of songs. Defaults to 50.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            ensure_all_artist_songs (bool, optional): Whether to ensure that all artist songs are in the playlist, regardless of the number_of_songs specified. Defaults to True

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """
        if not (1 <= number_of_songs <= 1500):
            raise ValueError('Value for number_of_songs must be between 1 and 1500')

        artist_songs, _ = cls._filter_artist_songs(dataframe, artist_name)

        if artist_songs.empty:
            raise ValueError(f'{artist_name} does not exist in the playlist')

        df = cls._create_playlist_dataframe(artist_songs, number_of_songs, ensure_all_artist_songs)

        if build_playlist:
            cls._build_artist_playlist(
                user_id=user_id,
                artist_songs=df,
                artist_name=artist_name,
                base_playlist_name=base_playlist_name,
                ensure_all_artist_songs=ensure_all_artist_songs
            )

        return df.reset_index(drop=True)

    @classmethod
    def _find_recommendations_to_songs(cls, base_songs: pd.DataFrame, subset_name: str, all_genres: 'list[str]', all_artists: 'list[str]') -> Song:
        """Generates a song format record from a list of songs, with all the information the "song-based" recommendation needs

        Args:
            base_songs (list[dict[str, Any]]): List of base songs
            subset_name (str): Name of thihs subset of songs (barely seen, unless the dataframe is printed with this record in it)

        Returns:
            dict[str, Any]: New song fomat record with the information gathered from the list of base songs
        """
        artist_songs_genres = list(reduce(lambda acc, genres: acc + list(set(genres) - set(acc)), base_songs['genres'].to_list(), []))

        artist_songs_artists = list(reduce(lambda acc, artists: acc + list(set(artists) - set(acc)), base_songs['artists'].to_list(), []))

        song_dict = {
            'id': "",
            'lyrics': "",
            'name': subset_name,
            'genres': artist_songs_genres,
            'artists': artist_songs_artists,
            'tempo': float(base_songs['tempo'].mean()),
            'energy': float(base_songs['energy'].mean()),
            'valence': float(base_songs['valence'].mean()),
            'loudness': float(base_songs['loudness'].mean()),
            'popularity': round(base_songs['popularity'].mean()),
            'danceability': float(base_songs['danceability'].mean()),
            'vader_sentiment': float(base_songs['vader_sentiment'].mean()),
            'instrumentalness': float(base_songs['instrumentalness'].mean()),
            'genres_indexed': util.item_list_indexed(artist_songs_genres, all_items=all_genres),
            'artists_indexed': util.item_list_indexed(artist_songs_artists, all_items=all_artists),
        }

        return Song(**song_dict)


    @classmethod
    def artist_and_related_playlist(
        cls,
        user_id: str,
        artist_name: str,
        dataframe: pd.DataFrame,
        all_genres: 'list[str]',
        base_playlist_name: str,
        all_artists: 'list[str]',
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
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. ONLY TAKES EFFECT IF complete_with_similar == True AND number_of_songs > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """
        if not (1 <= number_of_songs <= 1500):
            raise ValueError('Value for number_of_songs must be between 1 and 1500')

        artist_songs, dataframe = cls._filter_artist_songs(dataframe, artist_name)

        if artist_songs.empty:
            raise ValueError(f'{artist_name} does not exist in the playlist')

        song = cls._find_recommendations_to_songs(
            all_genres=all_genres,
            base_songs=artist_songs,
            all_artists=all_artists,
            subset_name=f"{artist_name} Mix"
        )

        mix_songs = cls._get_recommendations(
            song=song,
            dataframe=dataframe,
            recommendation_type='artist-related',
            number_of_songs=number_of_songs - len(artist_songs) if len(artist_songs) < number_of_songs else len(artist_songs) // 3
        )

        ids = cls._concatenate_ids(artist_songs, mix_songs)

        df = cls._create_artist_dataframe(
            mix_songs=mix_songs,
            artist_songs=artist_songs,
            with_distance=with_distance
        )

        if print_base_caracteristics:
            cls._print_base_caracteristics(song)

        if build_playlist:
            cls._build_related_playlist(user_id, artist_name, base_playlist_name, ids)

        return df.reset_index(drop=True)


    @staticmethod
    def _concatenate_ids(artist_songs: pd.DataFrame, mix_songs: pd.DataFrame) -> 'list[str]':
        return pd.concat([artist_songs['id'], mix_songs['id']]).tolist()

    @staticmethod
    def _create_artist_dataframe(artist_songs: pd.DataFrame, mix_songs: pd.DataFrame, with_distance: bool) -> pd.DataFrame:
        columns = ['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence', 'vader_sentiment', 'lyrics']
        df = pd.concat([artist_songs[columns], mix_songs[columns]])

        if with_distance:
            df['distance'] = pd.to_numeric(0)
            columns.append('distance')

        return df[columns]

    @staticmethod
    def _print_base_caracteristics(song: Song):
        util.print_base_caracteristics(
            song.name,
            song.genres,
            song.artists,
            song.popularity,
            song.danceability,
            song.loudness,
            song.energy,
            song.instrumentalness,
            song.tempo,
            song.valence,
            song.vader_sentiment
        )

    @staticmethod
    def _build_related_playlist(user_id: str, artist_name: str, base_playlist_name: str, ids: 'list[str]'):
        playlist_type = 'artist-related'
        Library.write_playlist(
            ids=ids,
            user_id=user_id,
            artist_name=artist_name,
            playlist_type=playlist_type,
            base_playlist_name=base_playlist_name,
        )
    @staticmethod
    def _filter_artist_songs(dataframe: pd.DataFrame, artist_name: str) -> 'tuple[pd.DataFrame, pd.DataFrame]':
        return (
            dataframe[dataframe['artists'].apply(lambda artists: artist_name in artists)],
            dataframe[dataframe['artists'].apply(lambda artists: artist_name not in artists)]
        )

    @staticmethod
    def _create_playlist_dataframe(artist_songs: pd.DataFrame, number_of_songs: int, ensure_all_artist_songs: bool) -> pd.DataFrame:
        if ensure_all_artist_songs or len(artist_songs) < number_of_songs:
            df = artist_songs.copy()
        else:
            df = artist_songs.head(number_of_songs).copy()

        columns = ['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence', 'vader_sentiment', 'lyrics']
        df = df[columns]

        return df

    @staticmethod
    def _build_artist_playlist(user_id: str, artist_name: str, base_playlist_name: str, artist_songs: pd.DataFrame, ensure_all_artist_songs: bool):
        playlist_type = f'artist{"-full" if ensure_all_artist_songs else ""}'

        Library.write_playlist(
            user_id=user_id,
            artist_name=artist_name,
            playlist_type=playlist_type,
            ids=artist_songs['id'].tolist(),
            base_playlist_name=base_playlist_name,
        )

    @classmethod
    def audio_features_extraordinary_songs(cls, dataframe: pd.DataFrame) -> 'dict[str, dict]':
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
        df = dataframe[['id', 'name', 'artists', 'genres', 'popularity','added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence', 'vader_sentiment', 'lyrics']]

        return {
            'max_loudness': cls._get_extreme_song(df, 'loudness', ascending=False),
            'min_loudness': cls._get_extreme_song(df, 'loudness', ascending=True),
            'max_danceability': cls._get_extreme_song(df, 'danceability', ascending=False),
            'min_danceability': cls._get_extreme_song(df, 'danceability', ascending=True),
            'max_energy': cls._get_extreme_song(df, 'energy', ascending=False),
            'min_energy': cls._get_extreme_song(df, 'energy', ascending=True),
            'max_instrumentalness': cls._get_extreme_song(df, 'instrumentalness', ascending=False),
            'min_instrumentalness': cls._get_extreme_song(df, 'instrumentalness', ascending=True),
            'max_tempo': cls._get_extreme_song(df, 'tempo', ascending=False),
            'min_tempo': cls._get_extreme_song(df, 'tempo', ascending=True),
            'max_valence': cls._get_extreme_song(df, 'valence', ascending=False),
            'min_valence': cls._get_extreme_song(df, 'valence', ascending=True),
            'max_vader_sentiment': cls._get_extreme_song(df, 'vader_sentiment', ascending=False),
            'min_vader_sentiment': cls._get_extreme_song(df, 'vader_sentiment', ascending=True),
        }

    @staticmethod
    def _get_extreme_song(df: pd.DataFrame, feature: str, ascending: bool) -> dict:
        sorted_df = df.sort_values(feature, ascending=ascending)

        return sorted_df.iloc[0].to_dict()

    @classmethod
    def audio_features_statistics(cls, dataframe: pd.DataFrame) -> 'dict[str, float]':
        """FUnctions that returns the statistics (max, min and mean) for the audio features within the playlist

        Returns:
            dict[str, float]: The dictionary with the statistics
        """
        df: pd.DataFrame = dataframe[['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'loudness', 'energy', 'instrumentalness', 'tempo', 'valence', 'vader_sentiment', 'lyrics']]

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
            'min_vader_sentiment': df['vader_sentiment'].min(),
            'max_vader_sentiment': df['vader_sentiment'].max(),
            'mean_vader_sentiment': df['vader_sentiment'].mean(),
        }

    @classmethod
    def get_playlist_recommendation(
        cls,
        user_id: str,
        dataframe: pd.DataFrame,
        base_playlist_name: str,
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
            ValueError: main_criteria must be one of the following: 'mixed', 'artists', 'tracks', 'genres'

        Returns:
            pd.DataFrame: Recommendations playlist
        """

        if not (1 < number_of_songs <= 100):
            raise ValueError('number_of_songs must be between 1 and 100')

        if main_criteria not in ['mixed', 'artists', 'tracks', 'genres']:
            raise ValueError("main_criteria must be one of the following: 'mixed', 'artists', 'tracks', 'genres'")

        tracks = cls._get_tracks(main_criteria)
        genres = cls._get_genres(dataframe, time_range, main_criteria)
        artists = cls._get_artists(dataframe, time_range, main_criteria)

        audio_statistics = cls.audio_features_statistics(dataframe=dataframe)

        url = f'{BASE_URL}/recommendations?limit={number_of_songs}'

        url = cls._build_recommendation_url(url, main_criteria, tracks, genres, artists, audio_statistics)

        recommendations = RequestHandler.get_request(url=url).json()

        songs = SongUtil._build_song_objects(recommendations=recommendations)
        recommendations_playlist = pd.DataFrame(data=songs)

        ids = recommendations_playlist['id'].tolist()

        if build_playlist:
            Library.write_playlist(
                ids=ids,
                user_id=user_id,
                date=save_with_date,
                time_range=time_range,
                criteria=main_criteria,
                base_playlist_name=base_playlist_name,
                playlist_type='playlist-recommendation',
            )

        return recommendations_playlist

    @classmethod
    def _get_artists(cls, dataframe: pd.DataFrame, time_range: str, main_criteria: str) -> 'list[str]':
        if main_criteria not in ['genres', 'tracks']:
            top_artists = cls.get_playlist_trending_artists(dataframe=dataframe, time_range=time_range)
            top_artists_names = top_artists['name'][1:6].tolist()

            return [
                UserHandler.search(search_type='artist', limit=1, query=x).json()['artists']['items'][0]['id']
                for x in top_artists_names
            ]

        return []

    @staticmethod
    def _get_tracks(main_criteria: str) -> 'list[str]':
        if main_criteria not in ['artists']:
            return [
                track['id']
                for track in UserHandler.top_tracks(time_range='short_term', limit=5).json()['items']
            ]

        return []

    @classmethod
    def _get_genres(cls, dataframe: pd.DataFrame, time_range: str, main_criteria: str) -> 'list[str]':
        if main_criteria not in ['artists']:
            genres = cls.get_playlist_trending_genres(dataframe=dataframe, time_range=time_range)
            genres = genres['name'][1:6].tolist()[:5]
            return genres

        return []

    @staticmethod
    def _build_recommendation_url(
        url: str,
        main_criteria: str,
        tracks: 'list[str]',
        genres: 'list[str]',
        artists: 'list[str]',
        audio_statistics: 'dict[str, float]'
    ) -> str:
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
        min_instrumentalness = audio_statistics['min_instrumentalness'] * 0.8
        max_instrumentalness = audio_statistics['max_instrumentalness'] * 1.2
        target_instrumentalness = audio_statistics['mean_instrumentalness']

        if main_criteria == 'artists':
            url += f'&seed_artists={",".join(artists)}'
        elif main_criteria == 'genres':
            url += f'&seed_genres={",".join(genres[:4])}&seed_tracks={",".join(tracks[:1])}'
        elif main_criteria == 'mixed':
            url += f'&seed_tracks={",".join(tracks[:1])}&seed_artists={",".join(artists[:2])}&seed_genres={",".join(genres[:2])}'
        elif main_criteria == 'tracks':
            url += f'&seed_tracks={",".join(tracks[:2])}&seed_genres={",".join(genres[:3])}'

        url += f'&{min_tempo=!s}&{max_tempo=!s}&{target_tempo=!s}'
        url += f'&{min_energy=!s}&{max_energy=!s}&{target_energy=!s}'
        url += f'&{min_valence=!s}&{max_valence=!s}&{target_valence=!s}'
        url += f'&{min_danceability=!s}&{max_danceability=!s}&{target_danceability=!s}'
        url += f'&{min_instrumentalness=!s}&{max_instrumentalness=!s}&{target_instrumentalness=!s}'

        return url

    @staticmethod
    def _mood_constants() -> 'dict[str, dict[str, Any]]':
        return {
            'sad': {
                'ascending': True,
                'sorting': 'energy&valence',
                'query': 'valence < @valence_threshold and energy < @energy_threshold'
            },
            'calm': {
                'ascending': True,
                'sorting': 'energy&loudness',
                'query': 'valence >= @valence_threshold and energy < @energy_threshold and loudness < @loudness_threshold'
            },
            'angry': {
                'ascending': False,
                'sorting': 'energy&loudness',
                'query': 'valence < @valence_threshold and energy >= @energy_threshold and loudness >= @loudness_threshold'
            },
            'happy': {
                'ascending': False,
                'sorting': 'energy&valence',
                'query': 'valence >= @valence_threshold and energy >= @energy_threshold'
            }
        }


    @classmethod
    def get_songs_by_mood(
        cls,
        mood: str,
        user_id: str,
        dataframe: pd.DataFrame,
        base_playlist_name: str,
        number_of_songs: int = 50,
        build_playlist: bool = False,
        exclude_mostly_instrumental: bool = False
    ) -> pd.DataFrame:
        """Function to create playlists based on the general mood of a song

        Args:
            mood (str): The mood of the song. Can be 'happy', 'sad', or 'calm'
            number_of_songs (int, optional): Number of songs. Defaults to 50.
            build_playlist (bool, optional): Flag to create the playlist in the user's library. Defaults to False.
            exclude_mostly_instrumental (bool, optional): Flag to exclude the songs which are 80% or more instrumental. Defaults to False.

        Raises:
            ValueError: If the mood is not one of the valid options, the error is raised

        Returns:
            pd.DataFrame: A DataFrame containing the new playlist
        """
        if mood not in ['happy', 'sad', 'calm']:
            raise ValueError("The mood parameter must be one of the following: 'happy', 'sad', 'calm'")

        vader_positive = 0.3
        vader_negative = -0.3
        energy_threshold = 0.6
        valence_threshold = 0.5
        loudness_threshold = 0.5
        instrumentalness_threshold = 0.8

        mood_queries = cls._mood_constants()

        playlist = cls._create_playlist(
            dataframe=dataframe,
            vader_positive=vader_positive,
            vader_negative=vader_negative,
            query=mood_queries[mood]['query'],
            energy_threshold=energy_threshold,
            valence_threshold=valence_threshold,
            loudness_threshold=loudness_threshold,
            instrumentalness_threshold=instrumentalness_threshold,
            exclude_mostly_instrumental=exclude_mostly_instrumental,
        )

        playlist = cls._sort_playlist(
            playlist=playlist,
            sorting=mood_queries[mood]['sorting'],
            ascending=mood_queries[mood]['ascending']
        )

        playlist = cls._trim_playlist(
            mood=mood,
            playlist=playlist,
            number_of_songs=number_of_songs,
        )

        if build_playlist:
            ids = playlist['id'].tolist()
            Library.write_playlist(
                ids=ids,
                mood=mood,
                user_id=user_id,
                playlist_type='mood',
                base_playlist_name=base_playlist_name,
                exclude_mostly_instrumental=exclude_mostly_instrumental,
            )

        return playlist

    @staticmethod
    def _create_playlist(
        query: str,
        vader_positive: float,
        vader_negative: float,
        dataframe: pd.DataFrame,
        energy_threshold: float,
        valence_threshold: float,
        loudness_threshold: float,
        exclude_mostly_instrumental: bool,
        instrumentalness_threshold: float,
    ) -> pd.DataFrame:
        playlist = dataframe.query(query).copy()

        if exclude_mostly_instrumental:
            playlist = playlist.query('instrumentalness <= @instrumentalness_threshold')

        return playlist

    @staticmethod
    def _sort_playlist(playlist: pd.DataFrame, sorting: str, ascending: bool) -> pd.DataFrame:
        if sorting == 'energy&valence':
            playlist['mood_index'] = playlist['energy'] + 3 * playlist['valence'] + 2 * playlist['vader_sentiment']
        else:
            playlist['mood_index'] = playlist['energy'] + 3 * playlist['loudness'] + playlist['vader_sentiment']

        return playlist.sort_values(by='mood_index', ascending=ascending)

    @staticmethod
    def _trim_playlist(playlist: pd.DataFrame, number_of_songs: int, mood: str) -> pd.DataFrame:
        if len(playlist) >= number_of_songs:
            playlist = playlist.head(number_of_songs)
        else:

            logging.warning(f"The playlist does not contain {number_of_songs} {mood} songs. Therefore there are only {len(playlist)} in the returned playlist.")

        return playlist


    @classmethod
    def playlist_songs_based_on_most_listened_tracks(
            cls,
            user_id: str,
            all_genres: 'list[str]',
            dataframe: pd.DataFrame,
            base_playlist_name: str,
            all_artists: 'list[str]',
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
        if time_range not in {'short_term', 'medium_term', 'long_term'}:
            raise ValueError("time_range needs to be one of the following: 'short_term', 'medium_term', 'long_term'")

        top_50 = UserHandler.top_tracks(time_range=time_range, limit=50).json()

        songs = SongUtil._build_song_objects(recommendations=top_50, dict_key='items')

        df = pd.DataFrame(songs)

        most_listened_dict = cls._find_recommendations_to_songs(
            base_songs=df,
            all_genres=all_genres,
            all_artists=all_artists,
            subset_name='Most listened songs',
        )

        playlist = cls._get_recommendations(
            dataframe=dataframe,
            song=most_listened_dict,
            number_of_songs=number_of_songs,
            recommendation_type=time_range.split('_')[0],
        )

        if build_playlist:
            ids = playlist['id'].tolist()

            Library.write_playlist(
                ids=ids,
                user_id=user_id,
                time_range=time_range,
                base_playlist_name=base_playlist_name,
                playlist_type='most-listened-recommendation',
            )

        return playlist
