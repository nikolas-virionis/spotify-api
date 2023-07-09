import pandas as pd

from functools import reduce
from dataclasses import dataclass
from spotify_recommender_api.model.song import Song
from spotify_recommender_api.core.library import Library
from spotify_recommender_api.requests.request_handler import RequestHandler, BASE_URL

@dataclass
class User:
    user_id: str


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
        self._validate_input_parameters(number_of_songs, main_criteria, time_range)

        artists, genres = self._get_top_artists_genres(main_criteria, time_range)
        tracks = self._get_top_tracks(main_criteria, time_range)

        url = self._build_recommendations_url(number_of_songs, main_criteria, artists, genres, tracks)

        recommendations = RequestHandler.get_request(url=url).json()
        songs = self._build_song_objects(recommendations)

        recommendations_playlist = pd.DataFrame(data=songs)
        ids = recommendations_playlist['id'].tolist()

        if build_playlist:
            Library.write_playlist(
                ids=ids,
                user_id=self.user_id,
                time_range=time_range,
                criteria=main_criteria,
                save_with_date=save_with_date,
                playlist_type='profile-recommendation',
            )

        return recommendations_playlist


    @staticmethod
    def _validate_input_parameters(number_of_songs: int, main_criteria: str, time_range: str) -> None:
        """Validates the input parameters of the get_profile_recommendation method.

        Args:
            K (int): Number of songs in the recommendations playlist.
            main_criteria (str): Main criteria for the recommendations playlist.
            time_range (str): The time range to get the profile most listened information from.

        Raises:
            ValueError: If K is not between 1 and 100.
            ValueError: If main_criteria is not one of 'mixed', 'artists', 'tracks', 'genres'.
            ValueError: If time_range is not one of 'short_term', 'medium_term', 'long_term'.
        """
        if not 1 <= number_of_songs <= 100:
            raise ValueError('K must be between 1 and 100')

        valid_criteria = {'mixed', 'artists', 'tracks', 'genres'}
        if main_criteria not in valid_criteria:
            raise ValueError(f"main_criteria must be one of the following: {', '.join(valid_criteria)}")

        valid_time_range = {'short_term', 'medium_term', 'long_term'}
        if time_range not in valid_time_range:
            raise ValueError(f"time_range needs to be one of the following: {', '.join(valid_time_range)}")

    @staticmethod
    def _get_top_artists_genres(main_criteria: str, time_range: str) -> 'tuple[list[str], list[str]]':
        """Gets the top artists and genres based on the main criteria and time range.

        Args:
            main_criteria (str): Main criteria for the recommendations playlist.
            time_range (str): The time range to get the profile most listened information from.

        Returns:
            tuple[list[str], list[str]]: List of artist IDs and genres.
        """
        artists = []
        genres = []

        if main_criteria != 'tracks':
            top_artists_req = RequestHandler.get_request(url=f'{BASE_URL}/me/top/artists?time_range={time_range}&limit=5').json()['items']
            artists = [artist['id'] for artist in top_artists_req]
            genres = list(set(reduce(lambda x, y: x + y, [artist['genres'] for artist in top_artists_req], [])))[:5]

        return artists, genres

    @staticmethod
    def _get_top_tracks(main_criteria: str, time_range: str) -> 'list[str]':
        """Gets the top tracks based on the main criteria and time range.

        Args:
            main_criteria (str): Main criteria for the recommendations playlist.
            time_range (str): The time range to get the profile most listened information from.

        Returns:
            list[str]: List of track IDs.
        """
        if main_criteria not in ['artists']:
            return [
                track['id']
                for track in RequestHandler.get_request(
                    url=f'{BASE_URL}/me/top/tracks?time_range={time_range}&limit=5'
                ).json()['items']
            ]
        return []

    @staticmethod
    def _build_recommendations_url(K: int, main_criteria: str, artists: 'list[str]', genres: 'list[str]', tracks: 'list[str]') -> str:
        """Builds the URL for the recommendations based on the main criteria and seed data.

        Args:
            K (int): Number of songs in the recommendations playlist.
            main_criteria (str): Main criteria for the recommendations playlist.
            artists (list[str]): List of artist IDs.
            genres (list[str]): List of genres.
            tracks (list[str]): List of track IDs.

        Returns:
            str: URL for the recommendations.
        """
        url = f'{BASE_URL}/recommendations?limit={K}'

        if main_criteria == 'artists':
            url += f'&seed_artists{",".join(artists)}'
        elif main_criteria == 'genres':
            url += f'&seed_genres={",".join(genres[:4])}&seed_tracks={",".join(tracks[:1])}'
        elif main_criteria == 'mixed':
            url += f'&seed_tracks={",".join(tracks[:2])}&seed_artists={",".join(artists[:1])}&seed_genres={",".join(genres[:2])}'
        elif main_criteria == 'tracks':
            url += f'&seed_tracks={",".join(tracks)}'

        return url

    @staticmethod
    def _build_song_objects(recommendations: dict) -> 'list[Song]':
        """Builds a list of Song objects from the recommendations data.

        Args:
            recommendations (dict): Recommendations data.

        Returns:
            List[Song]: List of Song objects.
        """
        songs = []

        for song in recommendations["tracks"]:
            song_id, name, popularity, artists, _ = Song.song_data(song=song)
            song_genres = Song.get_song_genres(artists=artists)

            danceability, loudness, energy, instrumentalness, tempo, valence = Song.query_audio_features(song_id=song_id)

            songs.append(
                Song(
                    name=name,
                    id=song_id,
                    tempo=tempo,
                    energy=energy,
                    valence=valence,
                    loudness=loudness,
                    genres=song_genres,
                    popularity=popularity,
                    danceability=danceability,
                    instrumentalness=instrumentalness,
                    artists=[artist.name for artist in artists],
                )
            )

        return songs