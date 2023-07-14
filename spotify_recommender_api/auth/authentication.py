import os
import logging

from spotify_recommender_api.server import up_server

class AuthenticationHandler:
    """Class that contains both headers, with authentication, and authentication gathering actions"""

    _headers: 'dict[str, str]' = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


    @classmethod
    def _retrieve_local_access_token(cls) -> None:
        """Function that tries to retrieve the access token from the local file where it is stored. In case it does not exist it raises an exception"""
        try:

            with open('./.spotify-recommender-util/execution.txt', 'r') as f:
                cls._headers['Authorization'] = f'Bearer {f.readline()}'

        except FileNotFoundError as file_not_found:
            logging.debug('File not found: ', file_not_found)

            raise

        except Exception as e:
            logging.error('There was an error while validating the access token', e)
            raise


    @staticmethod
    def _cleanup_aux_files() -> None:
        """Function that removes the temporary auxiliary file used for the token retrieving action"""
        logging.debug('Cleaning up txt file used temporarily for retrieving the auth token')

        if os.path.exists("./.spotify-recommender-util/execution-status.txt"):
            os.remove("./.spotify-recommender-util/execution-status.txt")


    @classmethod
    def _retrive_new_token(cls) -> str:
        """Function that centralizes the new token retrieval actions

        Returns:
            str: The newly retrieved access token
        """
        logging.debug('Error while trying the existant auth token. Executing server to retrieve a new one.')

        up_server()

        with open('./.spotify-recommender-util/execution.txt', 'r') as f:
            auth_token = f.readline()

        cls._cleanup_aux_files()

        return auth_token
