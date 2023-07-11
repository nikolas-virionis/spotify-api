import logging
import datetime
import pytz
from typing import Union, Any

from spotify_recommender_api.requests.api_handler import APIHandler

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
            K (int): desired number K of neighbors to be returned
            additional_info (Any, optional): the song name when the type is 'song'. Defaults to None.

        Raises:
            ValueError: Value for K must be between 1 and 1500
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

    # def write_playlist(cls, type: str, K: int, additional_info: Union[str, 'list[str]', None] = None):
    #     """Function that writes a new playlist with the recommendations for the given type
    #     type: the type of the playlist being created ('song', 'short', 'medium'):
    #      - 'song': a playlist related to a song
    #      - 'short': a playlist related to the short term favorites for that given user
    #      - 'medium': a playlist related to the medium term favorites for that given user

    #     Note:
    #         This function will change the user's library by either creating a new plalylist or overriding the existing one

    #     Args:
    #         type (str): the type of the playlist being created
    #         K (int): desired number K of neighbors to be returned
    #         additional_info (Any, optional): the song name when the type is 'song'. Defaults to None.

    #     Raises:
    #         ValueError: Value for K must be between 1 and 1500
    #         ValueError: Invalid type
    #     """
    #     if K > 1500:
    #         logging.warning('K limit exceded. Maximum value for K is 1500')
    #         K = 1500
    #     elif K < 1:
    #         raise ValueError(f'Value for K must be between 1 and 1500 on creation of {type} playlist. {additional_info=!r}')

    #     if type == 'song':
    #         index = self.__get_index_for_song(additional_info)
    #         uris = f'spotify:track:{self.__song_dict[index]["id"]},'

    #         uris += ','.join([f'spotify:track:{neighbor}' for neighbor in self.__get_recommendations('song', additional_info, K)['id']])

    #     elif type in {'medium', 'short'}:
    #         ids = self.__medium_fav['id'] if type == 'medium' else self.__short_fav['id']

    #         uris = ','.join([f'spotify:track:{song}' for song in ids])

    #     elif any(x in type for x in ['most-listened', 'artist', '-recommendation', 'mood']):
    #         ids = additional_info
    #         if ids is None: # only because of strict type checking enforncing that if it can be None it souldnt be part of an iteration
    #             ids = []
    #         uris = ','.join([f'spotify:track:{song}' for song in ids])

    #     else:
    #         uris = ''
    #         raise ValueError('Invalid type')

    #     self.__build_playlist(type=type, uris=uris)

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
            playlist_tracks = cls._get_playlist_tracks(new_id)

            cls._delete_playlist_tracks(new_id, playlist_tracks)

            if cls._should_update_playlist_details(playlist_name, playlist_found[1]):
                cls._update_playlist_details(new_id, playlist_name, description)

        else:
            data = {
                "name": playlist_name,
                "description": description,
                "public": False
            }

            new_id = cls._create_new_playlist(user_id, data)

        return new_id

    @staticmethod
    def _get_playlist_info(playlist_type: str, base_playlist_name: Union[str, None] = None, **kwargs) -> 'tuple[str, str]':
        """Generates the playlist name and description based on the playlist type and additional information.

        Args:
            playlist_type (str): The type of playlist.
            base_playlist_name (str): The name of the base playlist.
            additional_info (Union[str, list[Any], None]): Additional information.

        Raises:
            ValueError: If additional information is None.

        Returns:
            tuple[str, str]: The playlist name and description.
        """

        if playlist_type == 'song':
            playlist_name = f"{kwargs['song_name']!r} Related"
            description = f"Songs related to {kwargs['song_name']!r}, within the playlist {base_playlist_name}"

        elif playlist_type in {'short', 'medium'}:
            playlist_name = "Recent-ish Favorites" if playlist_type == 'medium' else "Latest Favorites"
            description = f"Songs related to your {playlist_type} term top 5, within the playlist {base_playlist_name}"

        elif 'most-listened' in playlist_type and 'recommendation' not in playlist_type:
            term = playlist_type.replace('most-listened-', '')
            playlist_name = f"{term.replace('_', ' ').capitalize()} Most-listened Tracks"
            description = f"The most listened tracks in a {term.replace('_', ' ')} period"

        elif playlist_type == 'artist-related':
            playlist_name = f"{kwargs['artist_name']!r} Mix"
            description = f"Songs related to {kwargs['artist_name']!r}, within the playlist {base_playlist_name}"

        elif playlist_type == 'artist-full':
            playlist_name = f"This once was {kwargs['artist_name']!r}"
            description = f'''All {kwargs['artist_name']}'{"" if kwargs['artist_name'][-1] == "s" else "s"} songs, within the playlist {base_playlist_name}'''

        elif playlist_type == 'artist':
            playlist_name = f"This once was {kwargs['artist_name']!r}"
            description = f'''{kwargs['artist_name']}'{"" if kwargs['artist_name'][-1] == "s" else "s"} songs, within the playlist {base_playlist_name}'''

        elif playlist_type == 'profile-recommendation':
            criteria = kwargs['criteria'] if kwargs['criteria'] != 'mixed' else 'genres, tracks and artists'
            playlist_name = f"{kwargs['time_range'].replace('_', ' ').capitalize()} Profile Recommendation"
            description = f'''{kwargs['time_range'].replace('_', ' ').capitalize()} profile-based recommendations based on favorite {criteria}'''

            if kwargs['date']:
                now = datetime.datetime.now(tz=pytz.timezone('UTC'))
                playlist_name += f' ({criteria} - {now.strftime("%Y-%m-%d")})'
                description += f' - {now.strftime("%Y-%m-%d")} snapshot'
            else:
                playlist_name += f' ({criteria})'

        elif playlist_type == 'playlist-recommendation':
            criteria = kwargs['criteria'] if kwargs['criteria'] != 'mixed' else 'genres, tracks and artists'
            time_range = f"for the last {kwargs['time_range']}" if kwargs['time_range'] != 'all_time' else 'for all_time'
            playlist_name = f"Playlist Recommendation {time_range}"
            description = f'''Playlist-based recommendations based on favorite {criteria}, within the playlist {base_playlist_name} {time_range}'''

            if kwargs['date']:
                now = datetime.datetime.now(tz=pytz.timezone('UTC'))
                playlist_name += f' ({criteria} - {now.strftime("%Y-%m-%d")})'
                description += f' - {now.strftime("%Y-%m-%d")} snapshot'
            else:
                playlist_name += f' ({criteria})'

        elif playlist_type == 'general-recommendation':
            playlist_name = f"General Recommendation based on {kwargs['description_types']}"
            description = kwargs['description']

        elif playlist_type == 'mood':
            mood = kwargs['mood']
            playlist_name = f"{mood} Songs".capitalize()
            description = f'Songs related to the mood "{mood}"{", excluding the mostly instrumental songs" if kwargs["exclude_mostly_instrumental"] else ""}, within the playlist {base_playlist_name}'

        elif playlist_type == 'most-listened-recommendation':
            playlist_name = f"{kwargs['time_range'].replace('_', ' ')} most listened recommendations".capitalize() # type: ignore
            description = f"Songs related to the {kwargs['time_range'].replace('_', ' ')} most listened tracks, within the playlist {base_playlist_name}" # type: ignore

        else:
            raise ValueError('type not valid')

    # additional_information_by_type = {
    #         'song': {'song_name': getattr(self, '_SpotifyAPI__song_name', None)},
    #         'artist': {'artist_name': getattr(self, '_SpotifyAPI__artist_name', None)},
    #         'mood': {
    #             'mood': getattr(self, '_SpotifyAPI__mood', None),
    #             'exclude_mostly_instrumental': getattr(self, '_SpotifyAPI__exclude_mostly_instrumental', None),
    #         },
    #         'profile-recommendation': {
    #             'criteria': getattr(self, '_SpotifyAPI__profile_recommendation_criteria', None),
    #             'date': getattr(self, '_SpotifyAPI__profile_recommendation_date', None),
    #             'time_range': getattr(self, '_SpotifyAPI__profile_recommendation_time_range', None)
    #         },
    #         'playlist-recommendation': {
    #             'criteria': getattr(self, '_SpotifyAPI__playlist_recommendation_criteria', None),
    #             'date': getattr(self, '_SpotifyAPI__playlist_recommendation_date', None),
    #             'time_range': getattr(self, '_SpotifyAPI__playlist_recommendation_time_range', None)
    #         },
    #         'general-recommendation': {
    #             'description': getattr(self, '_SpotifyAPI__general_recommendation_description', None),
    #             'description_types': getattr(self, '_SpotifyAPI__general_recommendation_description_types', None)
    #         },
    #         'most-listened-recommendation': {'time_range': getattr(self, '_SpotifyAPI__most_listened_recommendation_time_range', None)},
    #     }

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
        total_playlist_count = APIHandler.get_total_playlist_count()

        playlists = []
        for offset in range(0, total_playlist_count, 50):
            request = APIHandler.library_playlists(limit=50, offset=offset).json()

            playlists += [(playlist['id'], playlist['name'], playlist['description']) for playlist in request['items']]

        return next(
            (
                playlist for playlist in playlists
                if (
                    playlist[1] == name or
                    (
                        name.lower().startswith('profile short term recommendation') and
                        playlist[1] == name.replace('Short term ', '')
                    )
                ) and
                (
                    ' Term Most-listened Tracks' in name or
                    f', within the playlist {base_playlist_name}' in playlist[2] or
                    'Recommendation (' in name
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
            for track in APIHandler.playlist_songs(playlist_id=playlist_id).json()['items']
        ]


    @staticmethod
    def _delete_playlist_tracks(playlist_id: str, playlist_tracks: 'list[dict[str, str]]') -> None:
        """Deletes tracks from a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            playlist_tracks (list[dict[str, str]]): The tracks in the playlist.
        """
        APIHandler.delete_playlist_songs(
            playlist_id=playlist_id,
            playlist_tracks=playlist_tracks
        )


    @staticmethod
    def _should_update_playlist_details(playlist_name: str, found_playlist_name: str) -> bool:
        """Checks if the playlist details should be updated.

        Args:
            playlist_name (str): The name of the playlist.
            found_playlist_name (str): The name of the found playlist.

        Returns:
            bool: True if the details should be updated, False otherwise.
        """
        return playlist_name.lower().startswith('short term profile recommendation') and found_playlist_name == playlist_name.replace('Short term ', '')


    @staticmethod
    def _update_playlist_details(playlist_id: str, playlist_name: str, description: str) -> None:
        """Updates the details of a playlist.

        Args:
            playlist_id (str): The ID of the playlist.
            playlist_name (str): The new name of the playlist.
            description (str): The new description of the playlist.
        """
        data = {
            "name": playlist_name,
            "description": description,
            "public": False
        }

        logging.info(f'Updating playlist {playlist_name} details')
        APIHandler.update_playlist_details(playlist_id=playlist_id, data=data)

    @staticmethod
    def _create_new_playlist(user_id: str, data: 'dict[str, Any]') -> str:
        """Creates a new playlist.

        Args:
            user_id (str): The Spotify User ID.
            data (dict[str, Any]): The data for creating the playlist.

        Returns:
            str: The ID of the newly created playlist.
        """
        playlist_creation = APIHandler.create_playlist(user_id=user_id, data=data)
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

            APIHandler.insert_songs_in_playlist(playlist_id=playlist_id, uris=uris)

        else:

            for offset in range(0, len(full_uris_list), 100):
                uris = ','.join(full_uris_list[offset:offset + min(len(full_uris_list) - offset, 100)])

                APIHandler.insert_songs_in_playlist(playlist_id=playlist_id, uris=uris)
