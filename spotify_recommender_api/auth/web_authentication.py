import os
import logging
import time

from spotify_recommender_api.server.server import SCOPES
from spotify_recommender_api.server.sensitive import CLIENT_ID

class AuthenticationHandlerWeb:
    """Class that contains both headers, with authentication, and authentication gathering actions"""

    @staticmethod
    def _retrieve_local_refresh_token() -> str:
        """Function that tries to retrieve the refresh token from the local file where it is stored. In case it does not exist it raises an exception"""
        from pyscript import window
        try:
            refresh_token = window.localStorage.getItem('spotify-recommender-refresh-token')

            if not refresh_token:
                raise FileNotFoundError('Refresh token not found')

            return refresh_token

        except Exception as refresh_token_error:
            logging.debug('Error while trying to retrieve the refresh token: ', refresh_token_error)

            raise


    @classmethod
    def _retrieve_local_access_token(cls) -> None:
        """Function that tries to retrieve the access token from the local file where it is stored. In case it does not exist it raises an exception"""
        from pyscript import window
        try:
            auth_token = window.localStorage.getItem('spotify-recommender-token')

            if not auth_token:
                raise FileNotFoundError('Auth token not found')

            return auth_token

        except Exception as auth_token_error:
            logging.debug('Error while trying to retrieve the auth token: ', auth_token_error)

            raise


    @classmethod
    def _retrive_new_token(cls) -> str:
        """Function that centralizes the new token retrieval actions

        Returns:
            str: The newly retrieved access token
        """
        from pyscript import window

        if any(p in window.location.href for p in ['localhost', '127.0.0']):
            redirect_uri = 'http://127.0.0.1:5500/spotify-api/interface/authorization.html'
        else:
            redirect_uri = 'https://spotify-recommender.free.nf/authorization.html'

        window.open(
            f'https://accounts.spotify.com/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={redirect_uri}&scope={" ".join(SCOPES)}',
            '_blank',
            'location=yes,height=570,width=520,scrollbars=yes,status=yes'
        )

        for i in range(300):
            try:
                auth_token = cls._retrieve_local_access_token()

                return auth_token
            except FileNotFoundError:
                logging.debug(f'Token not found. Seconds waited: {i + 1}. Seconds left to authenticate: {300 - i}')
                time.sleep(1)
        else:
            raise TimeoutError('Timeout while waiting for the token')

