import json
import time
import logging
import requests
import functools

from typing import Union, Callable, Any
from spotify_recommender_api.auth.authentication import AuthenticationHandler
from spotify_recommender_api.error import HTTPRequestError, TooManyRequestsError, AccessTokenExpiredError

BASE_URL = 'https://api.spotify.com/v1'

class RequestHandler:
    # TODO: docstring

    @classmethod
    def access_token_retry(func: Callable[..., Any]) -> Callable[..., Any]: # type: ignore
        @functools.wraps(func)
        def wrapper(cls, *args: Any, **kwargs: Any) -> Any:
            value = None
            for error_count in range(3):
                try:
                    value = func(cls, *args, **kwargs)

                except AccessTokenExpiredError as e:
                    logging.warning('Error due to the access token expiration')
                    RequestHandler.get_auth()

                    if error_count >= 2:
                        raise

                else:
                    break

            return value

        return wrapper


    @classmethod
    def _validate_token(cls) -> bool:
        try:
            cls.get_request(url='https://api.spotify.com/v1/search?q=NF&type=artist&limit=1').json()['artists']
            # If the access token is not valid the AccessTokenExpiredError exception will be raised, thereby invalidating it

            logging.debug('Access token validation successful')

            return True

        except AccessTokenExpiredError as access_token_error:
            logging.debug('Access token expired. Error: ', access_token_error)

            raise

        except Exception as e:
            logging.error('There was an error while validating the access token', e)
            raise


    @classmethod
    def get_auth(cls) -> None:
        """Function to retrieve the authentication token
        """
        try:

            if auth_token := AuthenticationHandler._retrieve_local_access_token():
                cls._validate_token()

                logging.debug("Token is valid")

        except FileNotFoundError as file_not_found_error:
            logging.debug("File with auth token not found locally", file_not_found_error)

            auth_token = AuthenticationHandler._retrive_new_token()

        except AccessTokenExpiredError as access_token_expired_error:
            logging.debug("Access token expired", access_token_expired_error)

            auth_token = AuthenticationHandler._retrive_new_token()

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

                if response.status_code != 204 and 'error' in response.json():
                    raise HTTPRequestError(func_name=func.__name__, err_code=f"{response.status_code}: {response.json()['error']['message']}", message=None, *args, **kwargs)

                return response
            except Exception as e:
                if '401' in f'{e}':
                    logging.error('Access Token Expired')
                    raise AccessTokenExpiredError(func_name=func.__name__, message=None, *args, **kwargs) from e

                if '429' not in f'{e}':
                    raise HTTPRequestError(func_name=func.__name__, err_code=f"{response.status_code}: {response.json()['error']['message']}", message=None, *args, **kwargs) from e

                if x == 0:
                    logging.warning('\nExponential backoff triggered: ')

                x += 1

                if x >= retries:
                    raise TooManyRequestsError(func_name=func.__name__, message=f'After {retries} attempts, the execution of the function failed with the 429 exception', *args, **kwargs) from e

                sleep = 2 ** x
                logging.warning(f'\tError raised: sleeping {sleep} seconds')
                time.sleep(sleep)

        return requests.Response()

    @classmethod
    def get_request(cls, url: str, retries: int = 10) -> requests.Response:
        """GET request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.get, url=url, headers=AuthenticationHandler._headers, retries=retries)

    @classmethod
    def post_request(cls, url: str, data: Union[dict, None] = None, retries: int = 10) -> requests.Response:
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
    def post_request_dict(cls, url: str, data: Union[dict, None] = None, retries: int = 10) -> requests.Response:
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
    def post_request_with_auth(cls, url: str, data: Union[dict, None] = None, auth: Union['tuple[str, ...]', None] = None, retries: int = 10) -> requests.Response:
        """POST request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            data (dict, optional): Request body. Defaults to None.
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.post, url=url, headers=AuthenticationHandler._headers, data=data, auth=auth, retries=retries)

    @classmethod
    def put_request(cls, url: str, data: Union[dict, None] = None, retries: int = 10) -> requests.Response:
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
    def delete_request(cls, url: str, data: Union[dict, None] = None, retries: int = 10) -> requests.Response:
        """DELETE request with integrated exponential backoff retry strategy

        Args:
            url (str): Request URL
            data (dict, optional): Request body. Defaults to None.
            retries (int, optional): Number of retries. Defaults to 10.

        Returns:
            dict: Request response
        """
        return cls.exponential_backoff(func=requests.delete, url=url, headers=AuthenticationHandler._headers, data=json.dumps(data), retries=retries)
