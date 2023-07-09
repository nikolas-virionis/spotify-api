import pytz
import logging
import datetime
import spotify_recommender_api.util as util

from typing import Union, Any
from spotify_recommender_api.requests.request_handler import RequestHandler, BASE_URL

class Library:
    @classmethod
    def create_playlist(
            cls,
            type: str,
            user_id: str,
            base_playlist_name: str,
            additional_info: Union[str, 'list[Any]', None] = None,
            _update_created_playlists: bool = False
        ) -> Union[str, bool, None]:
        """Function that will return the empty playlist id, to be filled in later by the recommender songs
        This playlist may be a new one just created or a playlist that was previously created and now had all its songs removed

        Note:
            This function will change the user's library either making a new playlist or making an existing one empty

        Args:
            headers (dict): Request headers
            user_id (str): Spotify User id
            base_playlist_name (str): name of the base playlist
            additional_info (str, optional): name of the song, artist, or whatever additional information is needed. Defaults to None\n
            type (str): the type of the playlist being created ('song', 'short', 'medium'), meaning:\n
            --- 'song': a playlist related to a song\n
            --- 'short': a playlist related to the short term favorites for that given user\n
            --- 'medium': a playlist related to the medium term favorites for that given user\n
            --- 'most-listened-short': a playlist related to the short term most listened songs\n
            --- 'most-listened-medium': a playlist related to the medium term most listened songs\n
            --- 'most-listened-long': a playlist related to the long term most listened songs\n
            --- 'artist-related': a playlist related to a specific artist songs\n
            --- 'artist': a playlist containing only a specific artist songs\n

        Raises:
            ValueError: The type argument musts be one of the valid options

        Returns:
            str: The playlist id
        """
        if additional_info is None:
            return

        if type == 'song':
            playlist_name = f"{additional_info!r} Related"
            description = f"Songs related to {additional_info!r}, within the playlist {base_playlist_name}"
        elif type in {'short', 'medium'}:
            playlist_name = "Recent-ish Favorites" if type == 'medium' else "Latest Favorites"
            description = f"Songs related to your {type} term top 5, within the playlist {base_playlist_name}"

        elif 'most-listened' in type and 'recommendation' not in type:
            playlist_name = f"{type.replace('most-listened-', '').capitalize()} Term Most-listened Tracks"
            description = f"The most listened tracks in a {type.replace('most-listened-', '')} period of time"

        elif type == 'artist-related':
            playlist_name = f"{additional_info!r} Mix"
            description = f"Songs related to {additional_info!r}, within the playlist {base_playlist_name}"

        elif type == 'artist-full':
            playlist_name = f"This once was {additional_info!r}"
            description = f'''All {additional_info}'{"" if additional_info[-1] == "s" else "s"} songs, within the playlist {base_playlist_name}'''

        elif type == 'artist':
            playlist_name = f"This once was {additional_info!r}"
            description = f'''{additional_info}'{"" if additional_info[-1] == "s" else "s"} songs, within the playlist {base_playlist_name}'''

        elif type == 'profile-recommendation':
            criteria = additional_info[0] if additional_info[0] != 'mixed' else 'genres, tracks and artists'
            playlist_name = f"{additional_info[2].replace('_', ' ').capitalize()} Profile Recommendation"
            description = f'''{additional_info[2].replace('_', ' ').capitalize()} profile-based recommendations based on favorite {criteria}'''

            if additional_info[1]:
                now = datetime.datetime.now(tz=pytz.timezone('UTC'))
                playlist_name += f' ({criteria} - {now.strftime("%Y-%m-%d")})'
                description += f' - {now.strftime("%Y-%m-%d")} snapshot'
            else:
                playlist_name += f' ({criteria})'

        elif type == 'playlist-recommendation':
            criteria = additional_info[0] if additional_info[0] != 'mixed' else 'genres, tracks and artists'
            time_range = f'for the last {additional_info[2]}' if additional_info[2] != 'all_time' else 'for all_time'
            playlist_name = f"Playlist Recommendation {time_range}"
            description = f'''Playlist-based recommendations based on favorite {criteria}, within the playlist {base_playlist_name} {time_range}'''

            if additional_info[1]:
                now = datetime.datetime.now(tz=pytz.timezone('UTC'))
                playlist_name += f' ({criteria} - {now.strftime("%Y-%m-%d")})'
                description += f' - {now.strftime("%Y-%m-%d")} snapshot'
            else:
                playlist_name += f' ({criteria})'

        elif type == 'general-recommendation':
            playlist_name = f"General Recommendation based on {additional_info[1]}"
            description = additional_info[0]

        elif type == 'mood':
            playlist_name = f"{additional_info[0]} Songs".capitalize()
            description = f'Songs related to the mood "{additional_info[0]}"{", excluding the mostly instrumental songs" if additional_info[1] else ""}, within the playlist {base_playlist_name}'

        elif type == 'most-listened-recommendation':
            playlist_name = f"{additional_info.replace('_', ' ')} most listened recommendations".capitalize() # type: ignore
            description = f"Songs related to the {additional_info.replace('_', ' ')} most listened tracks, within the playlist {base_playlist_name}" # type: ignore

        else:
            raise ValueError('type not valid')

        if playlist_found := util.playlist_exists(name=playlist_name, base_playlist_name=base_playlist_name, _update_created_playlists=_update_created_playlists):
            new_id = playlist_found[0]

            playlist_tracks = [
                {'uri': track['track']['uri']}
                for track in RequestHandler.get_request(url=f'{BASE_URL}/playlists/{new_id}/tracks').json()['items']
            ]

            delete_json = RequestHandler.delete_request(
                data={"tracks": playlist_tracks},
                url=f'{BASE_URL}/playlists/{new_id}/tracks',
            ).json()

            if (
                _update_created_playlists or
                (
                    playlist_name.lower().startswith('short term profile recommendation') and
                    playlist_found[1] == playlist_name.replace('Short term ', '')
                )
            ):
                data = {
                    "name": playlist_name,
                    "description": description,
                    "public": False
                }

                logging.info(f'Updating playlist {playlist_found[1]} details')

                update_playlist_details = RequestHandler.put_request(url=f'{BASE_URL}/playlists/{new_id}', data=data)

        else:
            data = {
                "name": playlist_name,
                "description": description,
                "public": False
            }

            playlist_creation = RequestHandler.post_request(url=f'{BASE_URL}/users/{user_id}/playlists', data=data)
            new_id = playlist_creation.json()['id']

        return new_id