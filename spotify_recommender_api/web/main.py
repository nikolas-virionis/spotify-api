import json
import logging
import pandas as pd

from typing import Union
from pyscript import window
from spotify_recommender_api.user import User
from spotify_recommender_api.recommender import SpotifyAPI
from spotify_recommender_api.requests import RequestHandler

class SpotifyAPIWeb(SpotifyAPI):
    """Class that represents the SpotifyAPI for the Web

    This class is a subclass of the SpotifyAPI class, and it is used to represent the SpotifyAPI for the Web

    Attributes:
        - playlist_id (str): The id of the playlist, an unique big hash which identifies the playlist
        - user_id (str): The id of user, present in the user account profile
        - playlist_url (str): the url for the playlist, which is visible when trying to share it
        - liked_songs (bool): A flag to identify if the playlist to be mapped is the Liked Songs
    """
    def __init__(
        self, *,
        playlist_id: Union[str, None] = None,
        user_id: Union[str, None] = None,
        playlist_url: Union[str, None] = None,
        liked_songs: bool = False
    ) -> None:
        """Constructor for the SpotifyAPIWeb class

        Keyword Arguments:
            - playlist_id (str, optional, keyword-argument only): the id of the playlist, an unique big hash which identifies the playlist. Defaults to False.
            - user_id( str, optional, keyword-argument only): The id of user, present in the user account profile. Defaults to None.
            - playlist_url (str, optional, keyword-argument only): the url for the playlist, which is visible when trying to share it. Defaults to False.
            - liked_songs (bool, optional, keyword-argument only): A flag to identify if the playlist to be mapped is the Liked Songs. Defaults to False.
        """
        super().__init__(playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url, liked_songs=liked_songs)

    def _save_to_local_storage(self, playlist: pd.DataFrame, playlist_name: str) -> None:
        """Method that saves the playlist to the local storage

        This method saves the playlist to the local storage

        Arguments:
            - playlist (pd.DataFrame): The playlist to be saved

        Returns:
            str: The path to the saved file
        """
        playlist = playlist.to_dict('records')

        window.localStorage.setItem('playlist', json.dumps(playlist))

    def save_playlist_to_local_storage(self) -> None:
        playlist = self.get_playlist()

        self._save_to_local_storage(playlist)

    def get_playlist_from_local_storage(self) -> pd.DataFrame:
        """Method that retrieves the playlist from the local storage

        This method retrieves the playlist from the local storage

        Returns:
            pd.DataFrame: The playlist retrieved from the local storage
        """
        playlist = window.localStorage.getItem('playlist')

        if playlist is None:
            return pd.DataFrame()

        playlist = pd.DataFrame(json.loads(playlist))

        return playlist


def start_api_for_web(
    *,
    liked_songs: bool = False,
    log_level: str = 'DEBUG',
    user_id: Union[str, None] = None,
    playlist_url: Union[str, None] = None,
    playlist_id: Union[str, None] = None,
) -> SpotifyAPI:
    """Function that prepares for and initializes the API

    Note:
        Internet Connection is required

    Keyword Arguments:
        - log_level (str, optional, keyword-argument only): The log level, of the logging library, to be used. Defaults to WARNING
        - liked_songs (bool, optional, keyword-argument only): A flag to identify if the playlist to be mapped is the Liked Songs. Defaults to False.
        - user_id( str, optional, keyword-argument only): *Deprecated* The id of user, present in the user account profile. After version 5.4.0 it is retrieved via the api, instead. But for the purpose of backwars compatibility it is still available.
        - playlist_url (str, optional, keyword-argument only): the url for the playlist, which is visible when trying to share it. Defaults to False.
        - playlist_id (str, optional, keyword-argument only): the id of the playlist, an unique big hash which identifies the playlist. Defaults to False.

    Raises:
        ValueError: when passing the arguments, there should be only one or none filled between playlist_url, playlist_id and liked_songs

    Returns:
        SpotifyAPI: The instance of the SpotifyAPI class
    """
    logging.basicConfig(
        level=log_level.upper(),
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s',
    )

    logging.warning('After version 5.4.0 it has been noticed that more and more 429 errors are being raised, and no amount of exponential backoff can handle them, which are related to the Spotify API rate limits. If you encounter this error, please wait a little before trying again. If the problem persists, please submit an issue at the github repo, but close to the middle of July/2024 an extension request has been submitted to Spotify to increase the rate limits and if/when it is accepted, the problem will go away.')

    logging.info('Retrieving Authentication token')

    RequestHandler.get_auth(source='web')

    logging.debug('Authentication complete')

    if user_id is None:
        logging.debug('Retrieving User ID')
        user_id = User.retrieve_user_id()
        logging.info(f'Retrieved user id: {user_id}')
    else:
        logging.info('After version 5.4.0, the argument user_id is not mandatory, since it is now retrieved via the api. But when passed, it overrides this configuration')
        logging.info(f'Using user_id: {user_id}')

    return SpotifyAPIWeb(playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url, liked_songs=liked_songs)

