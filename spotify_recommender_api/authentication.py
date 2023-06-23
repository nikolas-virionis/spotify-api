import os
import logging
import spotify_recommender_api.request_handler as requests
from spotify_recommender_api.server import up_server


def get_auth() -> str:
    """Function to retrieve the authentication token for the first time in the execution

    Returns:
        str: Auth Token
    """

    with open('./.spotify-recommender-util/execution.txt', 'r') as f:
        try:
            auth_token = f.readline()

            requests.get_request(
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f'Bearer {auth_token}'
                },
                url='https://api.spotify.com/v1/search?q=NF&type=artist&limit=1'
            ).json()['artists']

        except Exception as e:
            logging.debug('Error while trying the existant auth token. Executing server to retrieve a new one.', e)

            up_server()

            with open('./.spotify-recommender-util/execution.txt', 'r') as f:
                auth_token = f.readline()

            if os.path.exists("./.spotify-recommender-util/execution-status.txt"):
                os.remove("./.spotify-recommender-util/execution-status.txt")

        return auth_token

