import logging
import traceback
import pandas as pd

from typing import Union
from dataclasses import dataclass
from spotify_recommender_api.user.util import UserUtil
from spotify_recommender_api.song.util import SongUtil
from spotify_recommender_api.core.library import Library
from spotify_recommender_api.playlist.base_playlist import BasePlaylist
from spotify_recommender_api.requests.request_handler import RequestHandler
from spotify_recommender_api.requests.api_handler import PlaylistHandler, UserHandler

@dataclass
class User:
    user_id: str

    def get_most_listened(self, time_range: str = 'long', number_of_songs: int = 50, build_playlist: bool = False) -> pd.DataFrame:
        """Function that creates the most-listened songs playlist for a given period of time in the users profile

        Args:
            time_range (str, optional): time range ('long_term', 'medium_term', 'short_term'). Defaults to 'long'.
            number_of_songs (int, optional): Number of the most listened songs to return. Defaults to 50.
            build_playlist (bool, optional): Build the playlist on the users library. Defaults to False

        Raises:
            ValueError: time range does not correspond to a valid time range ('long_term', 'medium_term', 'short_term')
            ValueError: Value for number_of_songs must be between 1 and 1500


        Returns:
            pd.DataFrame: pandas DataFrame containing the top number_of_songs songs in the time range
        """
        top = UserHandler.top_tracks(time_range=time_range, limit=number_of_songs).json()

        top_songs = SongUtil._build_song_objects(
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
            number_of_songs (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            main_criteria (str, optional): Main criteria for the recommendations playlist. Can be one of the following: 'mixed', 'artists', 'tracks', 'genres'. Defaults to 'mixed'.
            save_with_date (bool, optional): Flag to save the recommendations playlist as a Point in Time Snapshot. Defaults to False.
            build_playlist (bool, optional): Flag to build the recommendations playlist in the users library. Defaults to False.
            time_range (str, optional): The time range to get the profile most listened information from. Can be one of the following: 'short_term', 'medium_term', 'long_term'. Defaults to 'short_term'

        Raises:
            ValueError: If number_of_songs is not between 1 and 100.
            ValueError: If main_criteria is not one of 'mixed', 'artists', 'tracks', 'genres'.
            ValueError: If time_range is not one of 'short_term', 'medium_term', 'long_term'.

        Returns:
            pd.DataFrame: Recommendations playlist
        """
        UserUtil._validate_input_parameters(number_of_songs, main_criteria, time_range)

        artists, genres = UserUtil._get_top_artists_genres(main_criteria, time_range)
        tracks = UserUtil._get_top_tracks(main_criteria, time_range)

        url = UserUtil._build_recommendations_url(number_of_songs, main_criteria, artists, genres, tracks)

        recommendations = RequestHandler.get_request(url=url).json()
        songs = SongUtil._build_song_objects(recommendations)

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
        """Builds a general recommendation playlist.

        Args:
            number_of_songs (int, optional): Number of songs in the recommendations playlist. Defaults to 50.
            build_playlist (bool, optional): Flag to build the recommendations playlist in the user's library. Defaults to False.
            genres_info (Union[list[str], None], optional): List of genre names or None. Defaults to None.
            artists_info (Union[list[str], None], optional): List of artist names or None. Defaults to None.
            audio_statistics (Union[dict[str, float], None], optional): Dictionary of audio statistics or None. Defaults to None.
            tracks_info (Union[list[str], list[tuple[str, str]], list[list[str]], dict[str, str], None], optional): List or dictionary of track information or None. Defaults to None.

        Returns:
            pd.DataFrame: Recommendations playlist.
        """
        genres_info, artists_info, tracks_info = UserUtil._validate_input(number_of_songs, genres_info, artists_info, tracks_info)

        url = UserUtil._build_url(number_of_songs, genres_info, artists_info, tracks_info, audio_statistics)

        description, types = UserUtil._build_description(genres_info, artists_info, tracks_info)

        recommendations = UserUtil._get_recommendations(url)

        recommendations_playlist = UserUtil._build_playlist_dataframe(recommendations)

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

    def update_all_generated_playlists(
            self,
            base_playlist: Union[BasePlaylist, None] = None,
            *,
            playlist_types_to_update: 'Union[list[str], None]' = None,
            playlist_types_not_to_update: 'Union[list[str], None]' = None
        ) -> None:
        """Update all package generated playlists in batch

        Args:
            base_playlist (Union[BasePlaylist, None], optional): Base playlist object. Defaults to None.
            playlist_types_to_update (Union[list[str], None], optional): List of playlist types to update. Defaults to None.
            playlist_types_not_to_update (Union[list[str], None], optional): List of playlist types not to update. Defaults to None.
        """
        playlist_types_to_update = UserUtil._get_playlist_types_to_update(playlist_types_to_update, playlist_types_not_to_update)
        playlists = UserUtil._get_playlists_to_update(base_playlist=base_playlist, playlist_types_to_update=playlist_types_to_update)

        if not len(playlists):
            logging.info('No playlist found to be updated, given the playlist type filters')

        last_printed_perc_update = 0

        logging.info('Starting to update playlists')
        for index, (playlist_id, name, description, total_tracks) in enumerate(playlists):
            try:
                logging.debug(f'Updating song {name} - {index}/{len(playlists)}')

                perc_update = UserUtil._get_percentage_update(index, len(playlists))
                if last_printed_perc_update + 10 <= perc_update < 100:
                    logging.info(f'Playlists update operation at {perc_update}%')
                    last_printed_perc_update = perc_update

                if UserUtil._should_update_most_listened(name, playlist_types_to_update):
                    self.update_most_listened_playlist(total_tracks, name)

                elif UserUtil._should_update_profile_recommendation(name, playlist_types_to_update):
                    self.update_profile_recommendation_playlist(playlist_types_to_update, playlist_id, name, description, total_tracks)

                elif base_playlist is not None and UserUtil._should_update_base_playlist(name, description, base_playlist.playlist_name):
                    UserUtil._update_base_playlist(name, description, total_tracks, base_playlist, playlist_types_to_update)

            except ValueError as e:
                logging.error(f"Unfortunately we couldn't update the playlist {name} because\n {e} ")
                logging.debug(traceback.format_exc())

        logging.info('Playlists update operation at 100%')

    def update_most_listened_playlist(self, total_tracks: int, name: str) -> None:
        """Update the most listened playlist.

        Args:
            total_tracks (int): Total number of tracks.
            name (str): Name of the playlist.
        """
        self.get_most_listened(
            build_playlist=True,
            number_of_songs=total_tracks,
            time_range='_'.join(name.split(" ")[:2]).lower(),
        )

    def update_profile_recommendation_playlist(self, playlist_types_to_update: 'list[str]', playlist_id: str, name: str, description: str, total_tracks: int) -> None:
        """Update the profile recommendation playlist.

        Args:
            name (str): Name of the playlist.
            description (str): Description of the playlist.
        """
        criteria, time_range, playlist_name, playlist_description = UserUtil._prepare_profile_recommendation(name)

        if 'term' not in name.lower() or not description:
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
