
import requests

from typing import Union

class AuthHandler:
    @staticmethod
    def post_request_with_auth(url: str, data: Union[dict, None] = None, auth: Union['tuple[str, ...]', None] = None, retries: int = 10) -> requests.Response:
        """POST request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            data (dict, optional): Request body. Defaults to None.
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return requests.post(
            url=url,
            data=data,
            auth=auth
        )

    @classmethod
    def authorization_token(cls, auth_code: str, redirect_uri: str, client_id: str, client_secret: str) -> requests.Response:
        return cls.post_request_with_auth(
            auth=(client_id, client_secret),
            url="https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
            },
        )
