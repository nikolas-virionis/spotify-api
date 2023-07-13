import logging
import re
import pandas as pd

from typing import Union
from functools import reduce
from dataclasses import dataclass
from spotify_recommender_api.song import Song
from spotify_recommender_api.core.library import Library
from spotify_recommender_api.playlist.base_playlist import BasePlaylist
from spotify_recommender_api.requests.request_handler import RequestHandler, BASE_URL
from spotify_recommender_api.requests.api_handler import PlaylistHandler, LibraryHandler, UserHandler

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
        top = UserHandler.top_tracks(time_range=time_range, limit=number_of_songs).json()

        top_songs = Song._build_song_objects(
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
        songs = Song._build_song_objects(recommendations)

        recommendations_playlist = pd.DataFrame(data=songs)
        ids = recommendations_playlist['id'].tolist()

        if build_playlist:
            Library.write_playlist(
                ids=ids,
                date=save_with_date,
                user_id=self.user_id,
                time_range=time_range,
                criteria=main_criteria,
                playlist_type='profile-recommendation',
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
        songs = Song._build_song_objects(recommendations=recommendations)

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
        response = UserHandler.search(search_type='artist', query=artist, limit=1).json()

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
        response = UserHandler.search(search_type='track', query=f'{song} {artist}', limit=1).json()

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
            K (int): Number of songs in the recommendations playlist.
            main_criteria (str): Main criteria for the recommendations playlist.
            artists (list[str]): List of artist IDs.
            genres (list[str]): List of genres.
            tracks (list[str]): List of track IDs.

        Returns:
            str: URL for the recommendations.
        """
        url = f'{BASE_URL}/recommendations?limit={number_of_songs}'

        if main_criteria == 'artists':
            url += f'&seed_artists{",".join(artists)}'
        elif main_criteria == 'genres':
            url += f'&seed_genres={",".join(genres[:4])}&seed_tracks={",".join(tracks[:1])}'
        elif main_criteria == 'mixed':
            url += f'&seed_tracks={",".join(tracks[:2])}&seed_artists={",".join(artists[:1])}&seed_genres={",".join(genres[:2])}'
        elif main_criteria == 'tracks':
            url += f'&seed_tracks={",".join(tracks)}'

        return url

    def _build_url(
        self,
        number_of_songs: int,
        genres_info: 'list[str]',
        artists_info: 'list[str]',
        tracks_info: 'Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str]]',
        audio_statistics: 'Union[dict[str, float], None]' = None
    ) -> str:
        url = f'{BASE_URL}/recommendations?limit={number_of_songs}'

        if artists_info:
            url = self._add_seed_artists(url, artists_info)

        if genres_info:
            url = self._add_seed_genres(url, genres_info)

        if tracks_info:
            url = self._add_seed_tracks(url, tracks_info)

        if audio_statistics is not None:
            url = self._add_audio_features(url, audio_statistics)

        return url

    def update_all_generated_playlists(
            self,
            base_playlist: Union[BasePlaylist, None] = None,
            *,
            playlist_types_to_update: 'Union[list[str], None]' = None,
            playlist_types_not_to_update: 'Union[list[str], None]' = None
        ) -> None:
        """Update all package generated playlists in batch

        Arguments:
            playlist_types_to_update (list[str], optional): List of playlist types to update. For example, if you only want to update song-related playlists use this argument as ['song-related']. Defaults to all == ['most-listened-tracks', 'song-related', 'artist-mix', 'artist-full', 'playlist-recommendation', 'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation', 'mood', 'most-listened-recommendation'].
            playlist_types_not_to_update (list[str], optional): List of playlist types not to update. For example, if you want to update all playlists but song-related playlists use this argument as ['song-related']. it can be used alongside with the playlist_types_to_update but it can become confusing or redundant. Defaults to none == [].
        """
        playlist_types_to_update = self._get_playlist_types_to_update(playlist_types_to_update, playlist_types_not_to_update)

        playlists = self._get_playlists_to_update(base_playlist=base_playlist, playlist_types_to_update=playlist_types_to_update)

        last_printed_perc_update = 0

        for index, (playlist_id, name, description, total_tracks) in enumerate(playlists):
            try:
                logging.debug(f'Updating song {name} - {index}/{len(playlists)}')

                perc_update = self._get_percentage_update(index, len(playlists))
                if last_printed_perc_update + 10 <= perc_update < 100:
                    logging.info(f'Playlists update operation at {perc_update}%')
                    last_printed_perc_update = perc_update

                if self._should_update_most_listened(name, playlist_types_to_update):
                    self.get_most_listened(
                        build_playlist=True,
                        number_of_songs=total_tracks,
                        time_range='_'.join(name.split(" ")[:2]).lower(),
                    )

                elif self._should_update_profile_recommendation(name, playlist_types_to_update):
                    criteria, time_range, playlist_name, playlist_description = self._prepare_profile_recommendation(name)

                    if 'term' in name.lower() or not description:
                        data = {
                            "name": playlist_name,
                            "description": playlist_description,
                            "public": False
                        }

                        logging.info(f'Updating the name and description of the playlist {name} because of new time range specifications added to the profile_recommendation function in version 4.4.0')
                        logging.info('In case of any problems with the feature, submit an issue at: https://github.com/nikolas-virionis/spotify-api/issues')

                        PlaylistHandler.update_playlist_details(playlist_id=playlist_id, data=data)

                    if f"{time_range.replace('_', '-')}-profile-recommendation" in playlist_types_to_update:
                        self.get_profile_recommendation(
                            build_playlist=True,
                            time_range=time_range,
                            main_criteria=criteria,
                            number_of_songs=total_tracks,
                        )

                elif base_playlist is not None and self._should_update_base_playlist(name, description, base_playlist.playlist_name):
                    if self._should_update_song_related(name, playlist_types_to_update):
                        song_name = name.replace(" Related", '')[1:-1]
                        try:
                            artist_name = ' by '.join(description.split(', within the playlist')[0].split(' by ')[1:]) # joining just in case the artist name has " by " in it
                        except Exception:
                            artist_name = ''
                        self._update_song_related(base_playlist, song_name, artist_name, total_tracks)

                    elif self._should_update_artist_mix(name, playlist_types_to_update):
                        artist_name = name.replace(" Mix", '')[1:-1]
                        self._update_artist_mix(base_playlist, artist_name, total_tracks)

                    elif self._should_update_artist_full(name, playlist_types_to_update):
                        artist_name = name.replace("This once was ", '')[1:-1]
                        ensure_all_artist_songs = f'All {artist_name}' in description or not description
                        self._update_artist_full(base_playlist, artist_name, total_tracks, ensure_all_artist_songs)

                    elif self._should_update_playlist_recommendation(name, playlist_types_to_update):
                        criteria, time_range = self._parse_playlist_recommendation(name)
                        self._update_playlist_recommendation(base_playlist, time_range, criteria, total_tracks)

                    elif self._should_update_songs_by_mood(description, playlist_types_to_update):
                        mood = ' '.join(name.split(' ')[:-1]).lower()
                        exclude_mostly_instrumental = 'excluding the mostly instrumental songs' in description
                        self._update_songs_by_mood(base_playlist, mood, total_tracks, exclude_mostly_instrumental)

                    elif self._should_update_most_listened_recommendation(name, playlist_types_to_update):
                        time_range = '_'.join(name.split(' ')[:2]).lower()
                        self._update_most_listened_recommendation(base_playlist, time_range, total_tracks)

            except ValueError as e:
                logging.error(f"Unfortunately we couldn't update a playlist because\n {e}")

        logging.info('Playlists update operation at 100%')

    def _get_playlist_types_to_update(
        self,
        playlist_types_to_update: 'Union[list[str], None]',
        playlist_types_not_to_update: 'Union[list[str], None]'
    ) -> 'list[str]':
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

    def _get_playlists_to_update(self, playlist_types_to_update: 'list[str]', base_playlist: Union[BasePlaylist, None]) -> 'list[tuple[str, str, str, int]]':
        total_playlist_count = LibraryHandler.get_total_playlist_count()
        playlists = []

        for offset in range(0, total_playlist_count, 50):
            request = LibraryHandler.library_playlists(limit=50, offset=offset).json()
            playlists += [(playlist['id'], playlist['name'], playlist['description'], playlist['tracks']['total']) for playlist in request['items']]

        playlists = [
            playlist
            for playlist in playlists
            if self._playlist_needs_update(
                playlist=playlist,
                playlist_types_to_update=playlist_types_to_update,
                base_playlist_name=None if base_playlist is None else base_playlist.playlist_name
            )
        ]

        return playlists

    def _get_percentage_update(self, index: int, total_playlists: int) -> int:
        return next((perc for perc in range(100, 0, -10) if (100 * index) / total_playlists >= perc), 100)

    def _should_update_most_listened(self, name: str, playlist_types_to_update: 'list[str]') -> bool:
        return name in {'Long Term Most-listened Tracks', 'Medium Term Most-listened Tracks', 'Short Term Most-listened Tracks'} and 'most-listened-tracks' in playlist_types_to_update

    def _prepare_profile_recommendation(self, name: str) -> 'tuple[str, str, str, str]':
        criteria = name.split('(')[1].split(')')[0]
        criteria_name = criteria

        if ',' in criteria:
            criteria = 'mixed'

        if 'term' in name.lower():
            time_range = '_'.join(name.split(' ')[1:3]).lower()
        else:
            time_range = 'short_term'
        playlist_name = f"{time_range.replace('_', ' ').title()} Profile Recommendation ({criteria_name})"
        description = f'''{time_range.replace('_', ' ').capitalize()} Profile-based recommendations based on favorite {criteria_name}'''

        return criteria, time_range, playlist_name, description

    def _should_update_profile_recommendation(self, name: str, playlist_types_to_update: 'list[str]') -> bool:
        return (
            'Profile Recommendation' in name and
            ' - 20' not in name and
            any(
                playlist_type in playlist_types_to_update
                for playlist_type in {'short-term-profile-recommendation', 'medium-term-profile-recommendation', 'long-term-profile-recommendation'}
            )
        )
    def _should_update_base_playlist(self, name: str, description: str, base_playlist_name: str) -> bool:
        return (
            base_playlist_name is not None and
            (f", within the playlist {base_playlist_name}" in description or not description) and
            ('Related' in name or 'Mix' in name or 'This once was' in name or 'Playlist Recommendation' in name or 'Songs related to the mood' in description or 'most listened recommendations' in name)
        )

    def _should_update_song_related(self, name: str, playlist_types_to_update: 'list[str]') -> bool:
        return (re.match(r"\'(.*?)\' Related", name) or re.match(r'\"(.*?)\" Related', name)) and 'song-related' in playlist_types_to_update # type: ignore

    def _update_song_related(self, base_playlist: BasePlaylist, song_name: str, artist_name: str, total_tracks: int) -> None:
        base_playlist.get_recommendations_for_song(
            song_name=song_name,
            build_playlist=True,
            artist_name=artist_name,
            _auto_artist=not artist_name,
            number_of_songs=total_tracks - 1,
        )

    def _should_update_artist_mix(self, name: str, playlist_types_to_update: 'list[str]') -> bool:
        return (re.match(r"\'(.*?)\' Mix", name) or re.match(r'\"(.*?)\" Mix', name)) and 'artist-mix' in playlist_types_to_update # type: ignore

    def _update_artist_mix(self, base_playlist: BasePlaylist, artist_name: str, total_tracks: int) -> None:
        base_playlist.artist_and_related_playlist(
            build_playlist=True,
            artist_name=artist_name,
            number_of_songs=total_tracks,
        )

    def _should_update_artist_full(self, name: str, playlist_types_to_update: 'list[str]') -> bool:
        return (re.match(r"This once was \'(.*?)\'", name) or re.match(r'This once was \"(.*?)\"', name)) and 'artist-full' in playlist_types_to_update # type: ignore

    def _update_artist_full(self, base_playlist: BasePlaylist, artist_name: str, total_tracks: int, ensure_all_artist_songs: bool) -> None:
        base_playlist.artist_only_playlist(
            build_playlist=True,
            artist_name=artist_name,
            number_of_songs=total_tracks,
            ensure_all_artist_songs=ensure_all_artist_songs,
        )

    def _should_update_playlist_recommendation(self, name: str, playlist_types_to_update: 'list[str]') -> bool:
        return 'Playlist Recommendation' in name and ' - 20' not in name and 'playlist-recommendation' in playlist_types_to_update

    def _parse_playlist_recommendation(self, name: str) -> 'tuple[str, str]':
        criteria = name.split('(')[1].split(')')[0]
        if ',' in criteria:
            criteria = 'mixed'

        time_range = 'all_time' if 'for all_time' in name else name.split('for the last')[-1].split('(')[0].strip()

        return criteria, time_range

    def _update_playlist_recommendation(self, base_playlist: BasePlaylist, time_range: str, criteria: str, total_tracks: int) -> None:
        base_playlist.get_playlist_recommendation(
            build_playlist=True,
            time_range=time_range,
            main_criteria=criteria,
            number_of_songs=total_tracks,
        )

    def _should_update_songs_by_mood(self, description: str, playlist_types_to_update: 'list[str]') -> bool:
        return 'Songs related to the mood' in description and 'mood' in playlist_types_to_update

    def _update_songs_by_mood(self, base_playlist: BasePlaylist, mood: str, total_tracks: int, exclude_mostly_instrumental: bool) -> None:
        base_playlist.get_songs_by_mood(
            mood=mood,
            build_playlist=True,
            number_of_songs=total_tracks,
            exclude_mostly_instrumental=exclude_mostly_instrumental,
        )

    def _should_update_most_listened_recommendation(self, name: str, playlist_types_to_update: 'list[str]') -> bool:
        return 'most listened recommendations' in name and 'most-listened-recommendation' in playlist_types_to_update

    def _update_most_listened_recommendation(self, base_playlist: BasePlaylist, time_range: str, total_tracks: int) -> None:
        base_playlist.playlist_songs_based_on_most_listened_tracks(
            build_playlist=True,
            time_range=time_range,
            number_of_songs=total_tracks,
        )

    @staticmethod
    def _playlist_needs_update(playlist: 'tuple[str, str, str, int]', playlist_types_to_update: 'list[str]', base_playlist_name: Union[str, None] = None) -> bool:
        """Function to determine if a playlist inside the user's library needs to be updated

        Args:
            playlist (tuple[str, str, str, str]): Playlist information
            playlist_types_to_update (list[str]): Playlist types to be updated

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
