import requests

from typing import Union

class AuthHandler:
    """Class for handling authentication-related API requests."""

    @staticmethod
    def post_request_with_auth(url: str, data: Union[dict, None] = None, auth: Union['tuple[str, ...]', None] = None) -> requests.Response:
        """
        Send a POST request with integrated exponential backoff retry strategy.

        Args:
            url (str): The request URL.
            data (dict, optional): The request body. Default is None.
            auth (Union[tuple[str, ...], None], optional): The authentication credentials. Default is None.

        Returns:
            requests.Response: The response object containing the request response.
        """
        return requests.post(
            url=url,
            data=data,
            auth=auth
        )

    @classmethod
    def authorization_token(cls, auth_code: str, redirect_uri: str, client_id: str, client_secret: str) -> requests.Response:
        """
        Get an authorization token.

        Args:
            auth_code (str): The authorization code.
            redirect_uri (str): The redirect URI.
            client_id (str): The client ID.
            client_secret (str): The client secret.

        Returns:
            requests.Response: The response object containing the authorization token.
        """
        return cls.post_request_with_auth(
            auth=(client_id, client_secret),
            url="https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
            },
        )
