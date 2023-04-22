import os
from spotify_recommender_api.sensitive import *
from spotify_recommender_api.server import up_server
from spotify_recommender_api.request_handler import post_request_with_auth


def get_auth() -> str:
    """Function to retrieve the authentication token for the first time in the execution

    Returns:
        str: Auth Token
    """
    up_server()

    with open('./.spotify-recommender-util/execution.txt', 'r') as f:
        auth_token = f.readline()

    if os.path.exists("./.spotify-recommender-util/execution-status.txt"):
        os.remove("./.spotify-recommender-util/execution-status.txt")

    return auth_token


def refresh_token() -> str:
    """Function to refresh the auth token

    Returns:
        str: Refreshed auth token
    """

    print('Retrieving refresh token')

    with open('./.spotify-recommender-util/execution.txt', 'r') as f:
        refresh_token = f.readline()

    req = post_request_with_auth(
        url="https://accounts.spotify.com/api/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
    )

    token = req['access_token']

    with open('./.spotify-recommender-util/execution.txt', 'w') as f:
        f.write(token)

    return token
