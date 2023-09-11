import pandas as pd

from typing import Union
from spotify_recommender_api.song import Song


class KNNAlgorithm:

    @staticmethod
    def list_distance(indexed_list_a: 'list[int]', indexed_list_b: 'list[int]') -> float:
        """The weighted algorithm that calculates the distance between two songs according to either the distance between each song list of genres or the distance between each song list of artists

        Note:
            The "distance" is a mathematical value that represents how different two songs are, considering some parameter such as their genres or artists

        Note:
            For obvious reasons although both the parameters have two value options (genres, artists), when one of the parameters is specified as one of those, the other follows

        Args:
            indexed_list_a (list[int]): one song's list of genres or artists
            indexed_list_b (list[int]): counterpart song's list of genres or artists

        Returns:
            float: The distance between the two indexed lists
        """
        distance = 0
        for item_a, item_b in zip(indexed_list_a, indexed_list_b):
            # Here item_a being positive has more impact over item_b being positive, because
            # indexed_list_a is used as the song we are calculating the distance for, and
            # indexed_list_b is used as all the other songs that we are calculating the distance from indexed_list_a
            # for example if the base song (a) has the genre of pop and b does not, that is a significant increase in the distance from a to b
            # but if b has rap and pop and a only has pop, the rap difference is not as significant.
            if item_a == 1 and item_b == 0:
                distance += 0.4
            elif item_a == 0 and item_b == 1:
                distance += 0.2
            elif item_a == item_b == 1:
                distance -= 0.4

        return distance

    @staticmethod
    def calculate_total_distance(
            tempo_distance: float,
            genres_distance: float,
            energy_distance: float,
            valence_distance: float,
            artists_distance: float,
            loudness_distance: float,
            popularity_distance: float,
            artist_recommendation: bool,
            danceability_distance: float,
            vader_sentiment_distance: float,
            instrumentalness_distance: float
        ) -> float:
        """Function that uses the values for all the individual distances in a weighted equation to determine the total distance between the two songs

        Args:
            tempo_distance (float): The distance calculated for the tempo variable
            genres_distance (float): The distance calculated for the genres variable
            energy_distance (float): The distance calculated for the energy variable
            valence_distance (float): The distance calculated for the valence variable
            artists_distance (float): The distance calculated for the artists variable
            loudness_distance (float): The distance calculated for the loudness variable
            popularity_distance (float): The distance calculated for the popularity variable
            artist_recommendation (bool): A flag to indicate whether the distance is being calculated for an artist related recommendation
            danceability_distance (float): The distance calculated for the danceability variable
            instrumentalness_distance (float): The distance calculated for the instrumentalness variable

        Returns:
            float: Overall distance between the two songs
        """
        return (
            genres_distance * 0.8 +
            energy_distance * 0.65 +
            valence_distance * 0.93 +
            artists_distance * 0.38 +
            tempo_distance * 0.0025 +
            loudness_distance * 0.15 +
            danceability_distance * 0.25 +
            vader_sentiment_distance * 0.6 +
            instrumentalness_distance * 0.4 +
            popularity_distance * (0.003 if artist_recommendation else 0.015)
        )

    @classmethod
    def compute_distance(cls, song_a: 'dict[str, Union[float, list[str], int]]', song_b: 'dict[str, Union[float, list[str], int]]', artist_recommendation: bool = False) -> float: # type: ignore
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
            song_a (dict[str, Union[float, list[str], int]]): the song a, having all it's caracteristics
            song_b (dict[str, Union[float, list[str], int]]): the song b, having all it's caracteristics

        Returns:
            float: the distance between the two songs
        # """

        tempo_distance = abs(song_a['tempo'] - song_b['tempo']) # type: ignore
        energy_distance = abs(song_a['energy'] - song_b['energy']) # type: ignore
        valence_distance = abs(song_a['valence'] - song_b['valence']) # type: ignore
        loudness_distance = abs(song_a['loudness'] - song_b['loudness']) # type: ignore
        popularity_distance = abs(song_a['popularity'] - song_b['popularity']) # type: ignore
        danceability_distance = abs(song_a['danceability'] - song_b['danceability']) # type: ignore
        vader_sentiment_distance = abs(song_a['vader_sentiment'] - song_b['vader_sentiment']) # type: ignore
        genres_distance = cls.list_distance(song_a['genres_indexed'], song_b['genres_indexed']) # type: ignore
        artists_distance = cls.list_distance(song_a['artists_indexed'], song_b['artists_indexed']) # type: ignore
        instrumentalness_distance = abs(round(song_a['instrumentalness'], 2) - round(song_b['instrumentalness'], 2)) # type: ignore

        return cls.calculate_total_distance(
            tempo_distance=tempo_distance,
            genres_distance=genres_distance,
            energy_distance=energy_distance,
            valence_distance=valence_distance,
            artists_distance=artists_distance,
            loudness_distance=loudness_distance,
            popularity_distance=popularity_distance,
            danceability_distance=danceability_distance,
            artist_recommendation=artist_recommendation,
            vader_sentiment_distance=vader_sentiment_distance,
            instrumentalness_distance=instrumentalness_distance,
        )

    @classmethod
    def get_neighbors(cls, number_of_songs: int, dataframe: pd.DataFrame, song: Song, recommendation_type: str = 'song') -> pd.DataFrame:
        """Function to retrieve a number of the closest songs to one given song.

        Args:
            number_of_songs (int): Number of closest songs to gather
            dataframe (pd.DataFrame): Entire songbase, normally the provided playlist
            song (Song): The base song, the one the distances will be calculated from
            recommendation_type (str, optional): The recommendation type. Defaults to 'song'.

        Returns:
            pd.DataFrame: The recommendation songs in a dataframe
        """

        df: pd.DataFrame = dataframe.copy().query('id != @song.id')

        df['distance'] = df.apply(
            lambda row: cls.compute_distance(
                song_a=song.__dict__,
                song_b=row,
                artist_recommendation='artist' in recommendation_type
            ),
            axis=1
        )

        return df.sort_values(by='distance', ascending=True).head(number_of_songs)
