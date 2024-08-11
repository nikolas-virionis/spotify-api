import json
import time
import logging
import requests
import functools

from typing import Union, Callable, Any
from spotify_recommender_api.auth import AuthenticationHandler
from spotify_recommender_api.requests.auth_handler import AuthHandler
from spotify_recommender_api.server.sensitive import CLIENT_ID, CLIENT_SECRET
from spotify_recommender_api.error import HTTPRequestError, TooManyRequestsError, AccessTokenExpiredError

BASE_URL = 'https://api.spotify.com/v1'

class RequestHandler:
    """Class for handling API requests."""

    def access_token_retry(func: Callable[..., Any]) -> Callable[..., Any]: # type: ignore
        """
        Decorator to retry API requests with an updated access token.

        Args:
            func (Callable[..., Any]): The function to decorate.

        Returns:
            Callable[..., Any]: The decorated function.
        """
        @functools.wraps(func)
        def wrapper(cls, *args: Any, **kwargs: Any) -> Any:
            value = None
            for error_count in range(3):
                try:
                    value = func(cls, *args, **kwargs)

                except AccessTokenExpiredError as e:
                    logging.warning('Error due to the access token expiration')

                    try:
                        from pyscript import window
                        source = 'web'
                    except ImportError:
                        source = 'lib'

                    RequestHandler.get_auth(source=source)

                    if error_count >= 2:
                        raise

                else:
                    break

            return value

        return wrapper

    @staticmethod
    def get_refreshed_token(refresh_token: str) -> str:
        response = AuthHandler.post_request_with_auth(
            auth=(CLIENT_ID, CLIENT_SECRET),
            url="https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            },
        ).json()

        return response['access_token']

    @classmethod
    def _validate_token(cls) -> bool:
        """
        Validate the access token.

        Raises:
            AccessTokenExpiredError: If the access token has expired.

        Returns:
            bool: True if the access token is valid.
        """
        try:
            response = cls.get_request_no_retry(url='https://api.spotify.com/v1/me/top/tracks?time_range=long_term&limit=1')

            if response.status_code == 401:
                raise AccessTokenExpiredError('Access token expired')
            # If the access token is not valid the AccessTokenExpiredError exception will be raised, thereby invalidating it

            logging.debug('Access token validation successful')

            return True

        except AccessTokenExpiredError as access_token_error:
            logging.debug('Access token expired Error ')

            raise

        except Exception as e:
            logging.error('There was an error while validating the access token', e)
            raise


    @classmethod
    def get_auth(cls, source: str = 'lib') -> None:
        """
        Function to retrieve the authentication token.

        Args:
            source (str, optional): The source of the request. Defaults to 'lib' due to backwards compatibility.

        Raises:
            FileNotFoundError: If the file with the auth token is not found.
            AccessTokenExpiredError: If the access token has expired.
        """
        if source == 'lib':
            auth_handler = AuthenticationHandler
        else:
            from spotify_recommender_api.auth.web_authentication import AuthenticationHandlerWeb
            auth_handler = AuthenticationHandlerWeb
        try:
            auth_handler._retrieve_local_access_token()

            cls._validate_token()

            logging.debug("Token is valid")

            auth_token = AuthenticationHandler._headers["Authorization"].split(" ")[-1]

        except FileNotFoundError as file_not_found_error:
            logging.debug("File with auth token not found locally", file_not_found_error)

            auth_token = auth_handler._retrive_new_token()

        except AccessTokenExpiredError as access_token_expired_error:
            logging.debug("Access token expired")
            try:
                refresh_token = auth_handler._retrieve_local_refresh_token()

                auth_token = cls.get_refreshed_token(refresh_token)

                AuthenticationHandler._headers['Authorization'] = f'Bearer {auth_token}'

                cls._validate_token()

                logging.info('Token refreshed')

            except Exception as refresh_token_error:
                logging.debug('Error while trying to use the refresh token: ', refresh_token_error)

                auth_token = auth_handler._retrive_new_token()

        except Exception as e:
            logging.error('There was an error while validating the access token', e)
            raise

        AuthenticationHandler._headers['Authorization'] = f'Bearer {auth_token}'



    @classmethod
    @access_token_retry
    def exponential_backoff(cls, func: Callable[..., Any], retries: int = 5, *args, **kwargs) -> requests.Response:
        """Exponential backoff strategy (https://en.wikipedia.org/wiki/Exponential_backoff)
        in order to retry certain function after exponetially increasing delay, to overcome "429: Too Many Requests" error

        Args:
            func (function): function to be executed with exponential backoff
            retries (int, optional): Number of maximum retries before raising an exception. Defaults to 5.

        Raises:
            Exception: Error raised in the function after {retries} attempts

        Returns:
            Any: specified function return
        """
        x = 0
        while x <= retries:
            response = requests.Response()
            try:
                response: requests.Response = func(*args, **kwargs)

                try:
                    if response.status_code != 204 and 'error' in response.json():
                        raise HTTPRequestError(func_name=func.__name__, err_code=f"{response.status_code}", message=None, *args, **kwargs) # : {response.json()['error']['message']}
                except requests.exceptions.JSONDecodeError:
                    logging.debug(f'json decode error: {response.status_code} - {response.json()}')
                    return None


                return response
            except Exception as e:
                if response.status_code == 401:
                    logging.error('Access Token Expired')
                    raise AccessTokenExpiredError(func_name=func.__name__, message=None, *args, **kwargs) from e

                if response.status_code != 429 and response.status_code < 500:
                    raise HTTPRequestError(func_name=func.__name__, err_code=f"{response.status_code}", message=None, *args, **kwargs) from e # : {response.json()['error']['message']}

                if response.status_code >= 500:
                    logging.info('There has been an internal error in the Spotify API.')

                if x == 0:
                    logging.warning('\nExponential backoff triggered: ')

                x += 1

                if x >= retries:
                    raise TooManyRequestsError(func_name=func.__name__, message=f'After {retries} attempts, the execution of the function failed with the {response.status_code} exception', *args, **kwargs) from e

                sleep = 2 ** x
                logging.warning(f'\tError raised: sleeping {sleep} seconds')
                time.sleep(sleep)

        return requests.Response()

    @classmethod
    def get_request(cls, url: str, retries: int = 5) -> requests.Response:
        """GET request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.get, url=url, headers=AuthenticationHandler._headers, retries=retries)

    @classmethod
    def post_request(cls, url: str, data: Union[dict, None] = None, retries: int = 5) -> requests.Response:
        """POST request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            data (dict, optional): Request body. Defaults to None.
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.post, url=url, headers=AuthenticationHandler._headers, data=json.dumps(data), retries=retries)

    @classmethod
    def post_request_dict(cls, url: str, data: Union[dict, None] = None, retries: int = 5) -> requests.Response:
        """POST request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            data (dict, optional): Request body. Defaults to None.
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.post, url=url, headers=AuthenticationHandler._headers, data=data, retries=retries)

    @classmethod
    def put_request(cls, url: str, data: Union[dict, None] = None, retries: int = 5) -> requests.Response:
        """PUT request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            data (dict, optional): Request body. Defaults to None.
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.put, url=url, headers=AuthenticationHandler._headers, data=json.dumps(data), retries=retries)

    @classmethod
    def delete_request(cls, url: str, data: Union[dict, None] = None, retries: int = 5) -> requests.Response:
        """DELETE request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            data (dict, optional): Request body. Defaults to None.
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.delete, url=url, headers=AuthenticationHandler._headers, data=json.dumps(data), retries=retries)

    @classmethod
    def get_request_no_retry(cls, url: str) -> requests.Response:
        """GET request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return requests.get(url=url, headers=AuthenticationHandler._headers)
