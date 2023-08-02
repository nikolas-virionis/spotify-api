import re
import html
import logging
import pandas as pd

from typing import Union
from functools import reduce
from spotify_recommender_api.song.util import SongUtil
from spotify_recommender_api.playlist.base_playlist import BasePlaylist
from spotify_recommender_api.requests.api_handler import LibraryHandler, UserHandler
from spotify_recommender_api.requests.request_handler import RequestHandler, BASE_URL



class UserUtil:
    """Class for utility methods regarding song operations"""

    @classmethod
    def _update_base_playlist(cls, name: str, description: str, total_tracks: int, base_playlist: BasePlaylist, playlist_types_to_update: 'list[str]') -> None:
        """Update the base playlist.

        Args:
            name (str): Name of the playlist.
            description (str): Description of the playlist.
            total_tracks (int): Total number of tracks.
            base_playlist (BasePlaylist): Base playlist object.
            playlist_types_to_update (list[str]): List of playlist types to be updated.
        """
        if cls._should_update_song_related(name, playlist_types_to_update):
            song_name = name.replace(" Related", '')[1:-1]
            try:
                artist_name = ' by '.join(description.split(', within the playlist')[0].split(' by ')[1:])  # joining just in case the artist name has " by " in it
            except Exception:
                artist_name = ''
            cls._update_song_related(base_playlist, song_name, artist_name, total_tracks)

        elif cls._should_update_artist_mix(name, playlist_types_to_update):
            artist_name = name.replace(" Mix", '')[1:-1]
            cls._update_artist_mix(base_playlist, artist_name, total_tracks)

        elif cls._should_update_artist_full(name, playlist_types_to_update):
            artist_name = name.replace("This once was ", '')[1:-1]
            ensure_all_artist_songs = f'All {artist_name}' in description or not description
            cls._update_artist_full(base_playlist, artist_name, total_tracks, ensure_all_artist_songs)

        elif cls._should_update_playlist_recommendation(name, playlist_types_to_update):
            criteria, time_range = cls._parse_playlist_recommendation(name)
            cls._update_playlist_recommendation(base_playlist, time_range, criteria, total_tracks)

        elif cls._should_update_songs_by_mood(description, playlist_types_to_update):
            mood = ' '.join(name.split(' ')[:-1]).lower()
            exclude_mostly_instrumental = 'excluding the mostly instrumental songs' in description
            cls._update_songs_by_mood(base_playlist, mood, total_tracks, exclude_mostly_instrumental)

        elif cls._should_update_most_listened_recommendation(name, playlist_types_to_update):
            time_range = '_'.join(name.split(' ')[:2]).lower()
            cls._update_most_listened_recommendation(base_playlist, time_range, total_tracks)




    @classmethod
    def _build_url(
        cls,
        number_of_songs: int,
        genres_info: 'list[str]',
        artists_info: 'list[str]',
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]',
        audio_statistics: 'Union[dict[str, float], None]' = None
    ) -> str:
        """Build the URL for recommendations.

        Args:
            number_of_songs (int): Number of songs in the recommendations playlist.
            genres_info (list[str]): List of genre information.
            artists_info (list[str]): List of artist information.
            tracks_info (Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]): List of track information.
            audio_statistics (Union[dict[str, float], None], optional): Audio statistics for recommendations. Defaults to None.

        Returns:
            str: URL for recommendations.
        """
        url = f'{BASE_URL}/recommendations?limit={number_of_songs}'

        if artists_info:
            url = cls._add_seed_artists(url, artists_info)

        if genres_info:
            url = cls._add_seed_genres(url, genres_info)

        if tracks_info:
            url = cls._add_seed_tracks(url, tracks_info)

        if audio_statistics is not None:
            url = cls._add_audio_features(url, audio_statistics)

        return url

    @classmethod
    def _add_seed_artists(cls, url: str, artists_info: 'list[str]') -> str:
        """Add seed artists to the URL.

        Args:
            url (str): Base URL.
            artists_info (list[str]): List of artist information.

        Returns:
            str: Updated URL.
        """
        artists = [cls._get_artist_id(artist) for artist in artists_info]
        url += f'&seed_artists={",".join(artists)}'

        return url

    @classmethod
    def _add_seed_tracks(cls, url: str, tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]') -> str:
        """Add seed tracks to the URL.

        Args:
            url (str): Base URL.
            tracks_info (Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]): List of track information.

        Returns:
            str: Updated URL.
        """
        if isinstance(tracks_info, dict):
            tracks_info = tracks_info.items()  # type: ignore
        for track_info in tracks_info:
            song, artist = track_info if isinstance(track_info, (tuple, list)) else (track_info, '')
            track_id = cls._get_track_id(song, artist)
            url += f'&seed_tracks={track_id}'

        return url

    @staticmethod
    def _validate_input_parameters(number_of_songs: int, main_criteria: str, time_range: str) -> None:
        """Validate the input parameters of the get_profile_recommendation method.

        Args:
            number_of_songs (int): Number of songs in the recommendations playlist.
            main_criteria (str): Main criteria for the recommendations playlist.
            time_range (str): The time range to get the profile most listened information from.

        Raises:
            ValueError: If number_of_songs is not between 1 and 100.
            ValueError: If main_criteria is not one of 'mixed', 'artists', 'tracks', 'genres'.
            ValueError: If time_range is not one of 'short_term', 'medium_term', 'long_term'.
        """
        if not 1 <= number_of_songs <= 100:
            raise ValueError('number_of_songs must be between 1 and 100')

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
            top_artists_req = UserHandler.top_artists(time_range=time_range, limit=5).json()['items']
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
                for track in UserHandler.top_tracks(time_range=time_range, limit=5).json()['items']
            ]
        return []

    @staticmethod
    def _build_recommendations_url(number_of_songs: int, main_criteria: str, artists: 'list[str]', genres: 'list[str]', tracks: 'list[str]') -> str:
        """Builds the URL for the recommendations based on the main criteria and seed data.

        Args:
            number_of_songs (int): Number of songs in the recommendations playlist.
            main_criteria (str): Main criteria for the recommendations playlist.
            artists (list[str]): List of artist IDs.
            genres (list[str]): List of genres.
            tracks (list[str]): List of track IDs.

        Returns:
            str: URL for the recommendations.
        """
        url = f'{BASE_URL}/recommendations?limit={number_of_songs}'

        if main_criteria == 'artists':
            url += f'&seed_artists={",".join(artists)}'
        elif main_criteria == 'genres':
            url += f'&seed_genres={",".join(genres[:4])}&seed_tracks={",".join(tracks[:1])}'
        elif main_criteria == 'mixed':
            url += f'&seed_tracks={",".join(tracks[:2])}&seed_artists={",".join(artists[:1])}&seed_genres={",".join(genres[:2])}'
        elif main_criteria == 'tracks':
            url += f'&seed_tracks={",".join(tracks)}'

        return url

    @staticmethod
    def _playlist_needs_update(playlist: 'tuple[str, str, str, int]', playlist_types_to_update: 'list[str]', base_playlist_name: Union[str, None] = None) -> bool:
        """Function to determine if a playlist inside the user's library needs to be updated

        Args:
            playlist (tuple[str, str, str, str]): Playlist information
            playlist_types_to_update (list[str]): Playlist types to be updated
            base_playlist_name (str, optional): Name of the base playlist. Defaults to None.

        Returns:
            bool: The flag that indicates whether the playlist should be updated or not
        """
        _, name, description, _ = playlist

        if name in {'Long Term Most-listened Tracks', 'Medium Term Most-listened Tracks', 'Short Term Most-listened Tracks'} and 'most-listened-tracks' in playlist_types_to_update:
            return True

        elif (
            ' - 20' not in name and
            'Profile Recommendation' in name and
            any(
                playlist_type in playlist_types_to_update
                for playlist_type in {'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}
            )
        ):
            return True

        elif (not description or f', within the playlist {base_playlist_name}' in description) and base_playlist_name is not None:
            if (re.match(r"\'(.*?)\' Related", name) or re.match(r'\"(.*?)\" Related', name)) and 'song-related' in playlist_types_to_update:
                return True

            elif (re.match(r"\'(.*?)\' Mix", name) or re.match(r'\"(.*?)\" Mix', name)) and 'artist-mix' in playlist_types_to_update:
                return True

            elif (re.match(r"This once was \'(.*?)\'", name) or re.match(r'This once was \"(.*?)\"', name)) and 'artist-full' in playlist_types_to_update:
                return True

            elif 'Playlist Recommendation' in name and ' - 20' not in name and 'playlist-recommendation' in playlist_types_to_update:
                return True

            elif 'Songs related to the mood' in description and 'mood' in playlist_types_to_update:
                return True

            elif 'most listened recommendations' in name and 'most-listened-recommendation' in playlist_types_to_update:
                return True

        return False


    @staticmethod
    def _get_recommendations(url: str) -> dict:
        """Gets the recommendations from the specified URL.

        Args:
            url (str): The URL for the recommendations.

        Returns:
            dict: The recommendations data.
        """
        return RequestHandler.get_request(url=url).json()

    @staticmethod
    def _build_playlist_dataframe(recommendations: dict) -> pd.DataFrame:
        """Builds a DataFrame from the recommendations data.

        Args:
            recommendations (dict): The recommendations data.

        Returns:
            pd.DataFrame: The DataFrame containing the recommendations.
        """
        songs = SongUtil._build_song_objects(recommendations=recommendations)

        return pd.DataFrame(data=songs)

    @staticmethod
    def _build_description(
        genres_info: 'list[str]',
        artists_info: 'list[str]',
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]'
    ) -> 'tuple[str, list[str]]':
        """Builds the description for the recommendations playlist.

        Args:
            genres_info (list[str]): List of genres.
            artists_info (list[str]): List of artists.
            tracks_info (Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]): List of tracks.

        Returns:
            tuple[str, list[str]]: The description and the types of seed data used.
        """
        types = []
        description = 'General Recommendation based on '

        if artists_info:
            types.append('artists')
            description += f'the {"artist" if len(artists_info) == 1 else "artists"} '
            description += ' and '.join(', '.join(artists_info).rsplit(', ', 1))

        if genres_info:
            types.append('genres')
            if artists_info:
                description += ' and ' if len(artists_info) >= 1 else ', '
            description += f'the {"genre" if len(genres_info) == 1 else "genres"} '
            description += ' and '.join(', '.join(genres_info).rsplit(', ', 1))

        if tracks_info:
            types.append('tracks')
            if artists_info or genres_info:
                description += ' and ' if len(artists_info) + len(genres_info) >= 1 else ', '
            description += f'the {"track" if len(tracks_info) == 1 else "tracks"} '

            if isinstance(tracks_info, dict):
                description += ' and '.join(', '.join(list(tracks_info.keys())).rsplit(', ', 1))
            elif isinstance(tracks_info[0], (tuple, list)):
                description += ' and '.join(', '.join([track_info[0] for track_info in tracks_info]).rsplit(', ', 1))
            elif isinstance(tracks_info[0], str):
                description += ' and '.join(', '.join(tracks_info).rsplit(', ', 1)) # type: ignore

        return description, types

    @staticmethod
    def _add_audio_features(url: str, audio_statistics: 'dict[str, float]') -> str:
        """Adds audio features to the URL for recommendations.

        Args:
            url (str): The URL for recommendations.
            audio_statistics (dict[str, float]): The audio statistics.

        Returns:
            str: The updated URL with audio features.
        """
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

    @staticmethod
    def _get_artist_id(artist: str) -> str:
        """Gets the Spotify ID of an artist.

        Args:
            artist (str): The name of the artist.

        Returns:
            str: The Spotify ID of the artist.
        """
        response = UserHandler.search(search_type='artist', query=artist, limit=1).json()

        return response['artists']['items'][0]['id']

    @staticmethod
    def _add_seed_genres(url: str, genres_info: 'list[str]') -> str:
        """Adds seed genres to the URL for recommendations.

        Args:
            url (str): The URL for recommendations.
            genres_info (list[str]): List of genres.

        Returns:
            str: The updated URL with seed genres.
        """
        url += f'&seed_genres={",".join(genres_info)}'

        return url

    @staticmethod
    def _get_track_id(song: str, artist: str) -> str:
        """Gets the Spotify ID of a track.

        Args:
            song (str): The name of the song.
            artist (str): The name of the artist.

        Returns:
            str: The Spotify ID of the track.
        """
        response = UserHandler.search(search_type='track', query=f'{song} {artist}', limit=1).json()

        return response['tracks']['items'][0]['id']


    @staticmethod
    def _validate_input(
        number_of_songs: int,
        genres_info: 'Union[list[str], None]',
        artists_info: 'Union[list[str], None]',
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str], None]'
    ) -> 'tuple[list[str], list[str], Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]]':
        """Validates the input parameters for generating recommendations.

        Args:
            number_of_songs (int): Number of songs in the recommendations playlist.
            genres_info (Union[list[str], None]): List of genres.
            artists_info (Union[list[str], None]): List of artists.
            tracks_info (Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str], None]):
                List of tracks.

        Raises:
            ValueError: number_of_songs must be between 1 and 100
            ValueError: At least one of the three args must be provided: genres_info, artists_info, tracks_info
            ValueError: The sum of the number of items in each of the three args mustn't exceed 5

        Returns:
            tuple[list[str], list[str], Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]]:
                Validated and processed input parameters.
        """
        if not (1 <= number_of_songs <= 100):
            raise ValueError('number_of_songs must be between 1 and 100')

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
    def _get_playlist_types_to_update(
        playlist_types_to_update: 'Union[list[str], None]',
        playlist_types_not_to_update: 'Union[list[str], None]'
    ) -> 'list[str]':
        """Determines the types of playlists to update based on user preferences.

        Args:
            playlist_types_to_update (Union[list[str], None]): Playlist types to be updated.
            playlist_types_not_to_update (Union[list[str], None]): Playlist types not to be updated.

        Returns:
            list[str]: The types of playlists to update.
        """
        if playlist_types_to_update is None:
            playlist_types_to_update = [
                'most-listened-tracks', 'song-related', 'artist-mix', 'artist-full', 'playlist-recommendation',
                'short-term-profile-recommendation', 'medium-term-profile-recommendation',
                'long-term-profile-recommendation', 'mood', 'most-listened-recommendation'
            ]

        if playlist_types_not_to_update is None:
            playlist_types_not_to_update = []

        playlist_types_to_update = [playlist_type for playlist_type in playlist_types_to_update if playlist_type not in playlist_types_not_to_update]

        if 'profile-recommendation' in playlist_types_to_update:
            logging.warning('After version 4.4.0, the profile-recommendation playlists are separated in short, medium and long term. See the update_all_created_playlists docstring or the documentation at: https://github.com/nikolas-virionis/spotify-api')
            playlist_types_to_update.remove('profile-recommendation')
            for playlist_type in {'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}:
                if playlist_type not in playlist_types_to_update:
                    playlist_types_to_update.append(playlist_type)

        if 'profile-recommendation' in playlist_types_not_to_update:
            for playlist_type in {'profile-recommendation', 'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}:
                if playlist_type in playlist_types_to_update:
                    playlist_types_to_update.remove(playlist_type)

        return playlist_types_to_update

    @classmethod
    def _get_playlists_to_update(cls, playlist_types_to_update: 'list[str]', base_playlist: Union[BasePlaylist, None]) -> 'list[tuple[str, str, str, int]]':
        """Gets the playlists to update based on playlist types and base playlist.

        Args:
            playlist_types_to_update (list[str]): Types of playlists to update.
            base_playlist (Union[BasePlaylist, None]): Base playlist object.

        Returns:
            list[tuple[str, str, str, int]]: List of playlists to update.
        """

        logging.info('Starting to map the playlists which need to be updated')

        total_playlist_count = LibraryHandler.get_total_playlist_count()
        playlists = []

        for offset in range(0, total_playlist_count, 50):
            request = LibraryHandler.library_playlists(limit=50, offset=offset).json()
            playlists += [(playlist['id'], playlist['name'], playlist['description'], playlist['tracks']['total'] or 50) for playlist in request['items']]

        playlists = [
            playlist
            for playlist in playlists
            if cls._playlist_needs_update(
                playlist=playlist,
                playlist_types_to_update=playlist_types_to_update,
                base_playlist_name=None if base_playlist is None else base_playlist.playlist_name
            )
        ]

        logging.info('Playlists to be updated mapped successfully')

        return playlists

    @staticmethod
    def _get_percentage_update(index: int, total_playlists: int) -> int:
        """Calculates the percentage of playlists updated.

        Args:
            index (int): Index of the current playlist being updated.
            total_playlists (int): Total number of playlists to update.

        Returns:
            int: The percentage of playlists updated.
        """
        return next((perc for perc in range(100, 0, -10) if (100 * index) / total_playlists >= perc), 100)

    @staticmethod
    def _should_update_most_listened(name: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if the most listened playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the most listened playlist needs to be updated, False otherwise.
        """
        return name in {'Long Term Most-listened Tracks', 'Medium Term Most-listened Tracks', 'Short Term Most-listened Tracks'} and 'most-listened-tracks' in playlist_types_to_update

    @staticmethod
    def _prepare_profile_recommendation(name: str) -> 'tuple[str, str, str, str]':
        """Prepares the information for a profile recommendation playlist.

        Args:
            name (str): The name of the playlist.

        Returns:
            tuple[str, str, str, str]: The criteria, time range, playlist name, and description for the playlist.
        """
        criteria = name.split('(')[1].split(')')[0]
        criteria_name = criteria

        if ',' in criteria:
            criteria = 'mixed'

        if 'term' in name.lower():
            time_range = '_'.join(name.split(' ')[:2]).lower()
        else:
            time_range = 'short_term'
        playlist_name = f"{time_range.replace('_', ' ').title()} Profile Recommendation ({criteria_name})"
        description = f'''{time_range.replace('_', ' ').capitalize()} Profile-based recommendations based on favorite {criteria_name}'''

        return criteria, time_range, playlist_name, description

    @staticmethod
    def _should_update_profile_recommendation(name: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if the profile recommendation playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the profile recommendation playlist needs to be updated, False otherwise.
        """
        return (
            'Profile Recommendation' in name and
            ' - 20' not in name and
            any(
                playlist_type in playlist_types_to_update
                for playlist_type in {'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}
            )
        )

    @staticmethod
    def _should_update_base_playlist(name: str, description: str, base_playlist_name: str) -> bool:
        """Checks if a base playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            description (str): The description of the playlist.
            base_playlist_name (str): The name of the base playlist.

        Returns:
            bool: True if the base playlist needs to be updated, False otherwise.
        """
        return (
            base_playlist_name is not None and
            (f", within the playlist {base_playlist_name}" in description or not description) and
            ('Related' in name or 'Mix' in name or 'This once was' in name or 'Playlist Recommendation' in name or 'Songs related to the mood' in description or 'most listened recommendations' in name)
        )

    @staticmethod
    def _should_update_song_related(name: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if a song related playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the song related playlist needs to be updated, False otherwise.
        """
        return (re.match(r"\'(.*?)\' Related", name) or re.match(r'\"(.*?)\" Related', name)) and 'song-related' in playlist_types_to_update # type: ignore

    @staticmethod
    def _update_song_related(base_playlist: BasePlaylist, song_name: str, artist_name: str, total_tracks: int) -> None:
        """Updates a song-related playlist by getting recommendations for a specific song.

        Args:
            base_playlist (BasePlaylist): The base playlist object.
            song_name (str): The name of the song.
            artist_name (str): The name of the artist.
            total_tracks (int): The total number of tracks in the playlist (excluding the target song).

        Returns:
            None
        """
        base_playlist.get_recommendations_for_song(
            song_name=song_name,
            build_playlist=True,
            _auto_artist=not artist_name,
            number_of_songs=total_tracks - 1,
            artist_name=html.unescape(artist_name),
        )


    @staticmethod
    def _should_update_artist_mix(name: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if an artist mix playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the artist mix playlist needs to be updated, False otherwise.
        """
        return (re.match(r"\'(.*?)\' Mix", name) or re.match(r'\"(.*?)\" Mix', name)) and 'artist-mix' in playlist_types_to_update # type: ignore


    @staticmethod
    def _update_artist_mix(base_playlist: BasePlaylist, artist_name: str, total_tracks: int) -> None:
        """Updates an artist mix playlist by creating a playlist based on an artist and related artists.

        Args:
            base_playlist (BasePlaylist): The base playlist object.
            artist_name (str): The name of the artist.
            total_tracks (int): The total number of tracks in the playlist.

        Returns:
            None
        """
        base_playlist.artist_and_related_playlist(
            build_playlist=True,
            artist_name=artist_name,
            number_of_songs=total_tracks,
        )


    @staticmethod
    def _should_update_artist_full(name: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if an artist full playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the artist full playlist needs to be updated, False otherwise.
        """
        return (re.match(r"This once was \'(.*?)\'", name) or re.match(r'This once was \"(.*?)\"', name)) and 'artist-full' in playlist_types_to_update # type: ignore


    @staticmethod
    def _update_artist_full(base_playlist: BasePlaylist, artist_name: str, total_tracks: int, ensure_all_artist_songs: bool) -> None:
        """Updates an artist full playlist by creating a playlist containing all songs by an artist.

        Args:
            base_playlist (BasePlaylist): The base playlist object.
            artist_name (str): The name of the artist.
            total_tracks (int): The total number of tracks in the playlist.
            ensure_all_artist_songs (bool): Flag to ensure all songs by the artist are included.

        Returns:
            None
        """
        base_playlist.artist_only_playlist(
            build_playlist=True,
            artist_name=artist_name,
            number_of_songs=total_tracks,
            ensure_all_artist_songs=ensure_all_artist_songs,
        )


    @staticmethod
    def _should_update_playlist_recommendation(name: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if a playlist recommendation playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the playlist recommendation playlist needs to be updated, False otherwise.
        """
        return 'Playlist Recommendation' in name and ' - 20' not in name and 'playlist-recommendation' in playlist_types_to_update


    @staticmethod
    def _parse_playlist_recommendation(name: str) -> 'tuple[str, str]':
        """Parses the criteria and time range from a playlist recommendation playlist name.

        Args:
            name (str): The name of the playlist.

        Returns:
            tuple[str, str]: The parsed criteria and time range.
        """
        criteria = name.split('(')[1].split(')')[0]
        if ',' in criteria:
            criteria = 'mixed'

        time_range = 'all_time' if 'for all_time' in name else name.split('for the last')[-1].split('(')[0].strip()

        return criteria, time_range


    @staticmethod
    def _update_playlist_recommendation(base_playlist: BasePlaylist, time_range: str, criteria: str, total_tracks: int) -> None:
        """Updates a playlist recommendation playlist by getting recommendations based on criteria and time range.

        Args:
            base_playlist (BasePlaylist): The base playlist object.
            time_range (str): The time range for the playlist.
            criteria (str): The criteria for the recommendations.
            total_tracks (int): The total number of tracks in the playlist.

        Returns:
            None
        """
        base_playlist.get_playlist_recommendation(
            build_playlist=True,
            time_range=time_range,
            main_criteria=criteria,
            number_of_songs=total_tracks,
        )


    @staticmethod
    def _should_update_songs_by_mood(description: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if a songs by mood playlist needs to be updated.

        Args:
            description (str): The description of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the songs by mood playlist needs to be updated, False otherwise.
        """
        return 'Songs related to the mood' in description and 'mood' in playlist_types_to_update


    @staticmethod
    def _update_songs_by_mood(base_playlist: BasePlaylist, mood: str, total_tracks: int, exclude_mostly_instrumental: bool) -> None:
        """Updates a songs by mood playlist by getting songs related to a specific mood.

        Args:
            base_playlist (BasePlaylist): The base playlist object.
            mood (str): The mood to search for.
            total_tracks (int): The total number of tracks in the playlist.
            exclude_mostly_instrumental (bool): Flag to exclude mostly instrumental tracks.

        Returns:
            None
        """
        base_playlist.get_songs_by_mood(
            mood=mood,
            build_playlist=True,
            number_of_songs=total_tracks,
            exclude_mostly_instrumental=exclude_mostly_instrumental,
        )


    @staticmethod
    def _should_update_most_listened_recommendation(name: str, playlist_types_to_update: 'list[str]') -> bool:
        """Checks if a most listened recommendation playlist needs to be updated.

        Args:
            name (str): The name of the playlist.
            playlist_types_to_update (list[str]): Types of playlists to update.

        Returns:
            bool: True if the most listened recommendation playlist needs to be updated, False otherwise.
        """
        return 'most listened recommendations' in name and 'most-listened-recommendation' in playlist_types_to_update


    @staticmethod
    def _update_most_listened_recommendation(base_playlist: BasePlaylist, time_range: str, total_tracks: int) -> None:
        """Updates a most listened recommendation playlist by getting recommendations based on most listened tracks.

        Args:
            base_playlist (BasePlaylist): The base playlist object.
            time_range (str): The time range for the most listened tracks.
            total_tracks (int): The total number of tracks in the playlist.

        Returns:
            None
        """
        base_playlist.playlist_songs_based_on_most_listened_tracks(
            build_playlist=True,
            time_range=time_range,
            number_of_songs=total_tracks,
        )























































