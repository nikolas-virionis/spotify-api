import pandas as pd

from typing import Union
from functools import reduce
from dataclasses import dataclass
from spotify_recommender_api.model.song import Song
from spotify_recommender_api.core.library import Library
from spotify_recommender_api.request_handler import RequestHandler, BASE_URL

@dataclass
class User:
    user_id: str

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
        top = RequestHandler.get_request(url=f'https://api.spotify.com/v1/me/top/tracks?{time_range=!s}&limit={number_of_songs}').json()

        top_songs = self._build_song_objects(
            dict_key='items',
            recommendations=top,
        )

        dataframe = pd.DataFrame(data=top_songs)
        ids = dataframe['id'].tolist()

        if build_playlist:
            Library.write_playlist(
                ids=ids,
                user_id=self.user_id,
                playlist_type=f'most-listened-{time_range}',
            )

        return dataframe

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


    def get_general_recommendation2(
        self,
        audio_statistics: 'dict[str, float]',
        number_of_songs: int = 50,
        build_playlist: bool = False,
        genres_info: Union['list[str]', None] = None,
        artists_info: Union['list[str]', None] = None,
        use_main_playlist_audio_features: bool = False,
        tracks_info: Union['list[str]', 'list[tuple[str, str]]', 'list[list[str]]', 'dict[str, str]', None] = None,
    ) -> Union[pd.DataFrame, None]:
        """Builds a general recommendation based on up to 5 items spread across artists, genres, and tracks.

        Args:
            K (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            genres_info (list[str], optional): list of the genre names to be used in the recommendation. Defaults to [].
            artists_info (list[str], optional): list of the artist names to be used in the recommendation. Defaults to [].
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.
            use_main_playlist_audio_features (bool, optional): Flag to use the audio features of the main playlist to target better recommendations. Defaults to False.
            tracks_info (list[str] | list[tuple[str, str]] | list[list[str]] | dict[str, str]], optional): List of the song names to be used in the recommendations. They can be only the song names, but since there are a lot of songs with the same name i recommend using also the artist name in a key-value format using either a tuple, or list, or dict. Defaults to [].

        Raises:
            ValueError: K must be between 1 and 100
            ValueError: At least one of the three args must be provided: genres_info, artists_info, tracks_info
            ValueError: The sum of the number of items in each of the three args mustn't exceed 5
            ValueError: The argument tracks_info must be an instance of one of the following 4 types: list[str], list[tuple[str, str]], list[list[str]], dict[str, str]

        Returns:
            pd.DataFrame: Recommendations playlist
        """

        if not (1 <= number_of_songs <= 100):
            raise ValueError('K must be between 1 and 100')

        if not genres_info and not artists_info and not tracks_info:
            raise ValueError('At least one of the three args must be provided: genres_info, artists_info, tracks_info')

        if genres_info is None:
            genres_info = []

        if artists_info is None:
            artists_info = []

        if tracks_info is None:
            tracks_info = []

        if len(genres_info) + len(artists_info) + len(tracks_info) > 5:
            raise ValueError('The sum of the number of items in each of the three args mustn\'t exceed 5')

        url = f'https://api.spotify.com/v1/recommendations?limit={number_of_songs}'

        description = 'General Recommendation based on '

        types = []

        if artists_info:
            types.append('artists')
            description += 'the artists '
            for artist in artists_info:
                description += f'{artist}, '

            description = ' and '.join(description[:-2].rsplit(', ', 1))

            artists = [
                RequestHandler.get_request(
                    url=f'https://api.spotify.com/v1/search?q={artist}&type=artist&limit=1',
                ).json()['artists']['items'][0]['id']
                for artist in artists_info
            ]

            url += f'&seed_artists={",".join(artists)}'

            if len(artists_info) == 1:
                description = description.replace('artists', 'artist')

        if genres_info:
            types.append('genres')
            url += f'&seed_genres={",".join(genres_info)}'

            if artists_info and not tracks_info:
                description += ', and the genres '
                final_sep = ''
            elif not artists_info and tracks_info:
                description += 'the genres '
                final_sep = ', and the tracks '
            elif not artists_info:
                description += 'the genres '
                final_sep = ''
            else:  # both artists and tracks exist
                description += ', the genres '
                final_sep = ', and the tracks '

            for genre in genres_info:
                description += f'{genre}, '

            description = f"{' and '.join(description[:-2].rsplit(', ', 1)) if len(genres_info) > 1 else description[:-2]}{final_sep}"

            if len(genres_info) == 1:
                description = description.replace('genres', 'genre')

        if tracks_info:
            types.append('tracks')
            if artists_info and not genres_info:
                description += ', and the tracks '
            elif not artists_info and not genres_info:
                description += 'the tracks '

            if isinstance(tracks_info, dict):
                for song, artist in tracks_info.items():
                    description += f'{song} by {artist}, '

                tracks = [
                    RequestHandler.get_request(
                        url=f'https://api.spotify.com/v1/search?q={song} {artist}&type=track&limit=1',
                    ).json()['tracks']['items'][0]['id']
                    for song, artist in tracks_info.items()
                ]

            elif isinstance(tracks_info[0], (tuple, list)):
                for song, artist in tracks_info: # type: ignore because of the strict typing not recognizing that the condition above makes this a safe operation
                    description += f'{song} by {artist}, '
                tracks = [
                    RequestHandler.get_request(
                        url=f'https://api.spotify.com/v1/search?q={song} {artist}&type=track&limit=1',
                    ).json()['tracks']['items'][0]['id']
                    for song, artist in tracks_info # type: ignore because of the strict typing not recognizing that the condition above makes this a safe operation
                ]

            elif isinstance(tracks_info[0], str):
                for song in tracks_info:
                    description += f'{song}, '
                tracks = [
                    RequestHandler.get_request(
                        url=f'https://api.spotify.com/v1/search?q={song}&type=track&limit=1',
                    ).json()['tracks']['items'][0]['id']
                    for song in tracks_info
                ]

            else:
                raise ValueError('The argument tracks_info must be an instance of one of the following 4 types: list[str], list[tuple[str, str]], list[list[str]], dict[str, str]')

            description = ' and '.join(description[:-2].rsplit(', ', 1)) if len(artists_info) > 1 else description[:-2]

            url += f'&seed_tracks={",".join(tracks)}'

            if len(tracks_info) == 1:
                description = description.replace('tracks', 'track')

        if use_main_playlist_audio_features:
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

            url += f'&{min_tempo=!s}&{max_tempo=!s}&{target_tempo=!s}&{min_energy=!s}&{max_energy=!s}&{target_energy=!s}&{min_valence=!s}&{max_valence=!s}&{target_valence=!s}&{min_danceability=!s}&{max_danceability=!s}&{target_danceability=!s}&{min_instrumentalness=!s}&{max_instrumentalness=!s}&{target_instrumentalness=!s}'

        recommendations = RequestHandler.get_request(url=url).json()

        songs = self._build_song_objects(recommendations=recommendations)

        recommendations_playlist = pd.DataFrame(data=songs)

        if build_playlist:
            ids = recommendations_playlist['id'].tolist()
            types = ' and '.join(', '.join(types).rsplit(', ', 1)) if len(types) > 1 else types[0]

            Library.write_playlist(
                ids=ids,
                user_id=self.user_id,
                description=description,
                description_types=types,
                playlist_type='general-recommendation',
            )

        return recommendations_playlist

    def get_general_recommendation(
        self,
        number_of_songs: int = 50,
        build_playlist: bool = False,
        genres_info: 'Union[list[str], None]' = None,
        artists_info: 'Union[list[str], None]' = None,
        audio_statistics: 'Union[dict[str, float], None]' = None,
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str], None]' = None,
    ) -> pd.DataFrame:
        genres_info, artists_info, tracks_info = self._validate_input(number_of_songs, genres_info, artists_info, tracks_info)

        url = self._build_url(number_of_songs, genres_info, artists_info, tracks_info, audio_statistics)

        description, types = self._build_description(genres_info, artists_info, tracks_info)

        recommendations = self._get_recommendations(url)

        recommendations_playlist = self._build_playlist_dataframe(recommendations)

        if build_playlist:
            ids = recommendations_playlist['id'].tolist()
            types = ' and '.join(', '.join(types).rsplit(', ', 1)) if len(types) > 1 else types[0]

            Library.write_playlist(
                ids=ids,
                user_id=self.user_id,
                description=description,
                description_types=types,
                playlist_type='general-recommendation',
            )

        return recommendations_playlist

    def _get_recommendations(self, url: str) -> dict:
        return RequestHandler.get_request(url=url).json()

    def _build_playlist_dataframe(self, recommendations: dict) -> pd.DataFrame:
        songs = self._build_song_objects(recommendations=recommendations)

        return pd.DataFrame(data=songs)

    def _build_description(
        self,
        genres_info: 'list[str]',
        artists_info: 'list[str]',
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]'
    ) -> 'tuple[str, list[str]]':

        types = []
        description = 'General Recommendation based on '

        if artists_info:
            types.append('artists')
            description += f'the {"artist" if len(artists_info) == 1 else "artists"} '
            description += ', '.join(artists_info)

        if genres_info:
            types.append('genres')
            if artists_info:
                description += ' and ' if len(artists_info) >= 1 else ', '
            description += f'the {"genre" if len(genres_info) == 1 else "genres"} '
            description += ', '.join(genres_info)

        if tracks_info:
            types.append('tracks')
            if artists_info or genres_info:
                description += ' and ' if len(artists_info) + len(genres_info) >= 1 else ', '
            description += f'the {"track" if len(tracks_info) == 1 else "tracks"} '

            if isinstance(tracks_info, dict):
                description += ', '.join(list(tracks_info.keys()))
            elif isinstance(tracks_info[0], (tuple, list)):
                description += ', '.join([track_info[0] for track_info in tracks_info])
            elif isinstance(tracks_info[0], str):
                description += ', '.join(tracks_info) # type: ignore

        return description, types

    def _build_url(
        self,
        number_of_songs: int,
        genres_info: 'list[str]',
        artists_info: 'list[str]',
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]',
        audio_statistics: 'Union[dict[str, float], None]' = None
    ) -> str:
        url = f'https://api.spotify.com/v1/recommendations?limit={number_of_songs}'

        if artists_info:
            url = self._add_seed_artists(url, artists_info)

        if genres_info:
            url = self._add_seed_genres(url, genres_info)

        if tracks_info:
            url = self._add_seed_tracks(url, tracks_info)

        if audio_statistics is not None:
            url = self._add_audio_features(url, audio_statistics)

        return url

    def _add_audio_features(self, url: str, audio_statistics: 'dict[str, float]') -> str:
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

        url += f'&min_tempo={min_tempo}&max_tempo={max_tempo}&target_tempo={target_tempo}'
        url += f'&min_energy={min_energy}&max_energy={max_energy}&target_energy={target_energy}'
        url += f'&min_valence={min_valence}&max_valence={max_valence}&target_valence={target_valence}'
        url += f'&min_danceability={min_danceability}&max_danceability={max_danceability}&target_danceability={target_danceability}'
        url += f'&min_instrumentalness={min_instrumentalness}&max_instrumentalness={max_instrumentalness}&target_instrumentalness={target_instrumentalness}'

        return url


    def _add_seed_artists(self, url: str, artists_info: 'list[str]') -> str:
        artists = [self._get_artist_id(artist) for artist in artists_info]
        url += f'&seed_artists={",".join(artists)}'

        return url

    def _get_artist_id(self, artist: str) -> str:
        response = RequestHandler.get_request(
            url=f'https://api.spotify.com/v1/search?q={artist}&type=artist&limit=1',
        ).json()

        return response['artists']['items'][0]['id']

    def _add_seed_genres(self, url: str, genres_info: 'list[str]') -> str:
        url += f'&seed_genres={",".join(genres_info)}'

        return url


    def _add_seed_tracks(self, url: str, tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]') -> str:
        if isinstance(tracks_info, dict):
            tracks_info = tracks_info.items() # type: ignore
        for track_info in tracks_info:
            song, artist = track_info if isinstance(track_info, (tuple, list)) else (track_info, '')
            track_id = self._get_track_id(song, artist)
            url += f'&seed_tracks={track_id}'

        return url

    def _get_track_id(self, song: str, artist: str) -> str:
        response = RequestHandler.get_request(
            url=f'https://api.spotify.com/v1/search?q={song} {artist}&type=track&limit=1',
        ).json()
        return response['tracks']['items'][0]['id']


    def _validate_input(
        self,
        number_of_songs: int,
        genres_info: 'Union[list[str], None]',
        artists_info: 'Union[list[str], None]',
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str], None]'
    ) -> 'tuple[list[str], list[str], Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]]':
        if not (1 <= number_of_songs <= 100):
            raise ValueError('K must be between 1 and 100')

        if not genres_info and not artists_info and not tracks_info:
            raise ValueError('At least one of the three args must be provided: genres_info, artists_info, tracks_info')

        if genres_info is None:
            genres_info = []

        if artists_info is None:
            artists_info = []

        if tracks_info is None:
            tracks_info = []

        if len(genres_info) + len(artists_info) + len(tracks_info) > 5:
            raise ValueError('The sum of the number of items in each of the three args mustn\'t exceed 5')

        return genres_info, artists_info, tracks_info

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
    def _build_song_objects(recommendations: dict, dict_key: str = 'tracks') -> 'list[Song]':
        """Builds a list of Song objects from the recommendations data.

        Args:
            recommendations (dict): Recommendations data.

        Returns:
            List[Song]: List of Song objects.
        """
        songs = []

        for song in recommendations[dict_key]:
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