import pytz
import logging
import datetime
import contextlib

from typing import Union, Any
from spotify_recommender_api.requests import LibraryHandler, PlaylistHandler

class Library:

    @classmethod
    def write_playlist(cls, user_id: str, ids: 'list[str]', playlist_type: str, base_playlist_name: Union[str, None] = None, **kwargs) -> None:
        """Function that writes a new playlist with the recommendations for the given type
        type: the type of the playlist being created ('song', 'short', 'medium'):
         - 'song': a playlist related to a song
         - 'short': a playlist related to the short term favorites for that given user
         - 'medium': a playlist related to the medium term favorites for that given user

        Note:
            This function will change the user's library by either creating a new plalylist or overriding the existing one

        Args:
            type (str): the type of the playlist being created
            number_of_songs (int): desired number number_of_songs of neighbors to be returned
            additional_info (Any, optional): the song name when the type is 'song'. Defaults to None.

        Raises:
            ValueError: Value for number_of_songs must be between 1 and 1500
            ValueError: Invalid type
        """
        uris = ','.join([f'spotify:track:{song_id}' for song_id in ids])

        cls._build_playlist(
            uris=uris,
            user_id=user_id,
            playlist_type=playlist_type,
            base_playlist_name=base_playlist_name,
            **kwargs
        )

    @classmethod
    def _build_playlist(cls, user_id: str, playlist_type: str, uris: str, base_playlist_name: Union[str, None] = None, **kwargs) -> None:
        """Function that builds the contents of a playlist

        Note:
            This function will change the user's library by filling the previously created empty playlist

        Args:
            playlist_type (str): the type of the playlist being created
            uris (str): string containing all song uris in the format the Spotify API expects
        """
        if not uris:
            raise ValueError('Invalid value for the song uris')

        playlist_id = cls._create_playlist(
            user_id=user_id,
            playlist_type=playlist_type,
            base_playlist_name=base_playlist_name,
            **kwargs
        )

        cls._push_songs_to_playlist(full_uris=uris, playlist_id=playlist_id)


    @classmethod
    def _create_playlist(
        cls,
        user_id: str,
        playlist_type: str,
        base_playlist_name: Union[str, None] = None,
        **kwargs
    ) -> str:
        """Function that creates or empties a playlist and returns the playlist ID.

        Args:
            playlist_type (str): The type of playlist being created.
            user_id (str): The Spotify User ID.
            base_playlist_name (str): The name of the base playlist.

        Raises:
            ValueError: If the playlist type is invalid.

        Returns:
            Union[str, bool, None]: The playlist ID.
        """
        playlist_name, description = cls._get_playlist_info(
            playlist_type=playlist_type,
            base_playlist_name=base_playlist_name,
            **kwargs
        )

        if playlist_found := cls._find_existing_playlist(
            playlist_name=playlist_name,
            base_playlist_name=base_playlist_name
        ):
            new_id = playlist_found[0]

            if cls._should_update_playlist_details(playlist_name, playlist_found[1], new_id):
                cls._update_playlist_details(new_id, playlist_name, description)

            playlist_tracks = cls._get_playlist_tracks(new_id)
            cls._delete_playlist_tracks(new_id, playlist_tracks)

        else:
            data = {
                "name": playlist_name,
                "description": description,
                "public": False
            }

            new_id = cls._create_new_playlist(user_id, data)

        return new_id

    @classmethod
    def _get_playlist_info(cls, playlist_type: str, base_playlist_name: Union[str, None] = None, **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description based on the playlist type and additional information.

        Args:
            playlist_type (str): The type of playlist.
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments based on the playlist type.

        Raises:
            ValueError: If additional information is None.

        Returns:
            tuple[str, str]: The playlist name and description.
        """

        if playlist_type == 'song':
            return cls._get_song_playlist_info(base_playlist_name, **kwargs)

        if 'most-listened' in playlist_type and 'recommendation' not in playlist_type:
            return cls._get_most_listened_tracks_playlist_info(playlist_type)

        if playlist_type == 'artist-related':
            return cls._get_artist_related_playlist_info(base_playlist_name, **kwargs)

        if playlist_type == 'artist-full':
            return cls._get_artist_full_playlist_info(base_playlist_name, **kwargs)

        if playlist_type == 'artist':
            return cls._get_artist_playlist_info(base_playlist_name, **kwargs)

        if playlist_type == 'profile-recommendation':
            return cls._get_profile_recommendation_playlist_info(**kwargs)

        if playlist_type == 'playlist-recommendation':
            return cls._get_playlist_recommendation_playlist_info(base_playlist_name, **kwargs)

        if playlist_type == 'general-recommendation':
            return cls._get_general_recommendation_playlist_info(**kwargs)

        if playlist_type == 'mood':
            return cls._get_mood_playlist_info(base_playlist_name, **kwargs)

        if playlist_type == 'most-listened-recommendation':
            return cls._get_most_listened_recommendation_playlist_info(base_playlist_name, **kwargs)

        if 'recently-played-recommendations' in playlist_type:
            return cls._get_recently_played_recommendations_playlist_info(**kwargs)

        if 'recently-played' in playlist_type:
            return cls._get_recently_played_playlist_info(**kwargs)

        raise ValueError('Invalid playlist type')


    @staticmethod
    def _get_song_playlist_info(base_playlist_name: Union[str, None], **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a song-related playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        song_name = kwargs['song_name']
        artist_name = kwargs['artist_name']
        playlist_name = f"{song_name!r} Related"
        description = f"Songs related to {song_name!r} by {artist_name}, within the playlist {base_playlist_name}"
        return playlist_name, description


    @staticmethod
    def _get_most_listened_tracks_playlist_info(playlist_type: str) -> 'tuple[str, str]':
        """Generates the playlist name and description for a most listened tracks playlist.

        Args:
            playlist_type (str): The type of most listened tracks playlist.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        term = playlist_type.replace('most-listened-', '')
        playlist_name = f"{term.replace('_', ' ').title()} Most-listened Tracks"
        description = f"The most listened tracks in a {term.replace('_', ' ')} period"
        return playlist_name, description


    @staticmethod
    def _get_artist_related_playlist_info(base_playlist_name: Union[str, None], **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for an artist-related playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        artist_name = kwargs['artist_name']
        playlist_name = f"{artist_name!r} Mix"
        description = f"Songs related to {artist_name!r}, within the playlist {base_playlist_name}"
        return playlist_name, description


    @staticmethod
    def _get_artist_full_playlist_info(base_playlist_name: Union[str, None], **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for an artist full playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        artist_name = kwargs['artist_name']
        playlist_name = f"This once was {artist_name!r}"
        description = f"All {artist_name}'s songs, within the playlist {base_playlist_name}"
        return playlist_name, description


    @staticmethod
    def _get_artist_playlist_info(base_playlist_name: Union[str, None], **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for an artist playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        artist_name = kwargs['artist_name']
        playlist_name = f"This once was {artist_name!r}"
        description = f"{artist_name}'s songs, within the playlist {base_playlist_name}"
        return playlist_name, description


    @staticmethod
    def _get_profile_recommendation_playlist_info(**kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a profile recommendation playlist.

        Args:
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        criteria = kwargs['criteria'] if kwargs['criteria'] != 'mixed' else 'genres, tracks and artists'
        playlist_name = f"{kwargs['time_range'].replace('_', ' ').title()} Profile Recommendation"
        description = f"{kwargs['time_range'].replace('_', ' ').title()} profile-based recommendations based on favorite {criteria}"

        if kwargs['date']:
            now = datetime.datetime.now(tz=pytz.timezone('UTC'))
            playlist_name += f" ({criteria} - {now.strftime('%Y-%m-%d')})"
            description += f" - {now.strftime('%Y-%m-%d')} snapshot"
        else:
            playlist_name += f" ({criteria})"

        return playlist_name, description


    @staticmethod
    def _get_playlist_recommendation_playlist_info(base_playlist_name: Union[str, None], **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a playlist recommendation playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        criteria = kwargs['criteria'] if kwargs['criteria'] != 'mixed' else 'genres, tracks and artists'
        time_range = f"for the last {kwargs['time_range']}" if kwargs['time_range'] != 'all_time' else 'for all_time'
        playlist_name = f"Playlist Recommendation {time_range}"
        description = f"Playlist-based recommendations based on favorite {criteria}, within the playlist {base_playlist_name} {time_range}"

        if kwargs['date']:
            now = datetime.datetime.now(tz=pytz.timezone('UTC'))
            playlist_name += f" ({criteria} - {now.strftime('%Y-%m-%d')})"
            description += f" - {now.strftime('%Y-%m-%d')} snapshot"
        else:
            playlist_name += f" ({criteria})"

        return playlist_name, description


    @staticmethod
    def _get_general_recommendation_playlist_info(**kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a general recommendation playlist.

        Args:
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        playlist_name = f"General Recommendation based on {kwargs['description_types']}"
        description = kwargs['description']
        return playlist_name, description


    @staticmethod
    def _get_mood_playlist_info(base_playlist_name: Union[str, None], **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a mood playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        mood = kwargs['mood']
        exclude_mostly_instrumental = kwargs['exclude_mostly_instrumental']
        playlist_name = f"{mood} Songs".capitalize()
        description = f'Songs related to the mood "{mood}"'
        if exclude_mostly_instrumental:
            description += ", excluding the mostly instrumental songs"
        description += f", within the playlist {base_playlist_name}"
        return playlist_name, description


    @staticmethod
    def _get_most_listened_recommendation_playlist_info(base_playlist_name: Union[str, None], **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a most listened recommendation playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        time_range = kwargs['time_range'].replace('_', ' ')
        playlist_name = f"{time_range} most listened recommendations".capitalize()
        description = f"Songs related to the {time_range} most listened tracks, within the playlist {base_playlist_name}"
        return playlist_name, description

    @staticmethod
    def _get_recently_played_playlist_info(**kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a most listened recommendation playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        time_range = kwargs['time_range'].replace('-', ' ')
        playlist_name = f"Recently played songs in the {time_range}".capitalize()
        description = f"{'All ' if kwargs['all_songs'] else ''}Songs played in the {time_range}"

        if kwargs['save_with_date']:
            now = datetime.datetime.now(tz=pytz.timezone('UTC'))
            playlist_name += f" ({now.strftime('%Y-%m-%d')})"
            description += f" - {now.strftime('%Y-%m-%d')} snapshot"

        return playlist_name, description

    @staticmethod
    def _get_recently_played_recommendations_playlist_info(**kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description for a most listened recommendation playlist.

        Args:
            base_playlist_name (str): The name of the base playlist.
            **kwargs: Additional arguments.

        Returns:
            tuple[str, str]: The playlist name and description.
        """
        time_range = kwargs['time_range'].replace('-', ' ')
        criteria = kwargs['criteria']
        playlist_name = f"Recently played recommendations in the {time_range}".capitalize()
        description = f"Recommendation playlist based on {criteria} criteria of the recently played in the {time_range}"

        if kwargs['save_with_date']:
            now = datetime.datetime.now(tz=pytz.timezone('UTC'))
            playlist_name += f" ({criteria} - {now.strftime('%Y-%m-%d')})"
            description += f" - {now.strftime('%Y-%m-%d')} snapshot"
        else:
            playlist_name += f" ({criteria})"

        return playlist_name, description



    @classmethod
    def _find_existing_playlist(cls, playlist_name: str, base_playlist_name: Union[str, None]) -> 'Union[tuple[str, str, str], tuple[()]]':
        """Finds an existing playlist.

        Args:
            playlist_name (str): The name of the playlist.
            base_playlist_name (str): The name of the base playlist.
            _update_created_playlists (bool): Flag to update the details of an existing playlist.

        Returns:
            tuple[str, str, str] | tuple[()]: The playlist ID and name if found, otherwise an empty tuple.
        """
        return cls._playlist_exists(name=playlist_name, base_playlist_name=base_playlist_name)


    @staticmethod
    def _playlist_exists(name: str, base_playlist_name: Union[str, None]) -> 'Union[tuple[str, str, str], tuple[()]]':
        """Function used to check if a playlist exists inside the user's library
        Used before the creation of a new playlist

        Args:
            name (str): name of the playlist being created, which could easily be bypassed, if the playlist names were not made automatically
            base_playlist_name (str): name of the base playlist

        Returns:
            tuple[str, str, str] | tuple[()]: If the playlist already exists, returns the id of the playlist, otherwise returns False
        """
        total_playlist_count = LibraryHandler.get_total_playlist_count()

        playlists = []
        for offset in range(0, total_playlist_count, 50):
            request = LibraryHandler.library_playlists(limit=50, offset=offset).json()

            playlists += [(playlist['id'], playlist['name'], playlist['description']) for playlist in request['items']]

        return next(
            (
                playlist for playlist in playlists
                if (
                    playlist[1] == name or
                    (
                        name.lower().startswith('short term profile recommendation') and
                        playlist[1].strip() == name.replace('Short Term ', '').strip()
                    )
                ) and
                (
                    ' Term Most-listened Tracks' in playlist[1] or
                    f', within the playlist {base_playlist_name}' in playlist[2] or
                    'Recommendation (' in name or
                    'Recently played songs in the ' in name or
                    'Recently played recommendations in the ' in name or
                    not playlist[2]
                )
            ),
            ()
        )


    @staticmethod
    def _get_playlist_tracks(playlist_id: str) -> 'list[dict[str, str]]':
        """Gets the tracks of a playlist.

        Args:
            playlist_id (str): The ID of the playlist.

        Returns:
            list[dict[str, str]]: The tracks in the playlist.
        """
        return [
            {'uri': track['track']['uri']}
            for track in PlaylistHandler.playlist_songs(playlist_id=playlist_id).json()['items']
        ]


    @staticmethod
    def _delete_playlist_tracks(playlist_id: str, playlist_tracks: 'list[dict[str, str]]') -> None:
        """Deletes tracks from a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            playlist_tracks (list[dict[str, str]]): The tracks in the playlist.
        """
        PlaylistHandler.delete_playlist_songs(
            playlist_id=playlist_id,
            playlist_tracks=playlist_tracks
        )


    @staticmethod
    def _should_update_playlist_details(playlist_name: str, found_playlist_name: str, playlist_id: str) -> bool:
        """Checks if the playlist details should be updated.

        Args:
            playlist_name (str): The name of the playlist.
            found_playlist_name (str): The name of the found playlist.

        Returns:
            bool: True if the details should be updated, False otherwise.
        """
        playlist_details = PlaylistHandler.playlist_details(playlist_id).json()
        description = playlist_details.get('description')

        return (
            not description or
            (
                'mood' not in description.lower() and
                (
                    description.lower().startswith('songs related to') and
                    'Mix' not in playlist_name
                ) and
                'term most listened tracks' not in description.lower() and
                (
                    ' by ' not in description or
                    ' by ,' in description
                )
            ) or
            playlist_name.lower().startswith('short term profile recommendation') and
            found_playlist_name == playlist_name.replace('Short Term ', '')
        )


    @staticmethod
    def _update_playlist_details(playlist_id: str, playlist_name: str, description: str) -> None:
        """Updates the details of a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            playlist_name (str): The new name of the playlist.
            description (str): The new description of the playlist.
        """
        data = {
            "public": False,
            "name": playlist_name,
            "description": description,
        }

        logging.warning(f'Updating playlist {playlist_name} details')

        with contextlib.suppress(Exception):
            PlaylistHandler.update_playlist_details(playlist_id=playlist_id, data=data)

    @staticmethod
    def _create_new_playlist(user_id: str, data: 'dict[str, Any]') -> str:
        """Creates a new playlist.

        Args:
            user_id (str): The Spotify User ID.
            data (dict[str, Any]): The data for creating the playlist.

        Returns:
            str: The ID of the newly created playlist.
        """
        playlist_creation = LibraryHandler.create_playlist(user_id=user_id, data=data)
        return playlist_creation.json()['id']

    @classmethod
    def _push_songs_to_playlist(cls, full_uris: str, playlist_id: str) -> None:
        """Function to push soongs to a specified playlist

        Args:
            full_uris (str): list of song uri's
            playlist_id (str): playlist id
        """
        full_uris_list = full_uris.split(',')

        if len(full_uris_list) <= 100:
            uris = ','.join(full_uris_list)

            PlaylistHandler.insert_songs_in_playlist(playlist_id=playlist_id, uris=uris)

        else:
            for offset in range(0, len(full_uris_list), 100):
                uris = ','.join(full_uris_list[offset:offset + min(len(full_uris_list) - offset, 100)])

                PlaylistHandler.insert_songs_in_playlist(playlist_id=playlist_id, uris=uris)
