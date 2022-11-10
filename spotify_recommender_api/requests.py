import json
import time
from requests import get, post, delete, put


def exponential_backoff(func, retries: int = 5):
    # sourcery skip: raise-specific-error
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
        try:
            response = func()
            try:
                response.json()
            except Exception as e: # this error happens when there is a 204 response and the response.json() cannot be decoded properly regardless of the request being successful
                pass
            else:
                if response.status_code != 204 and 'error' in response.json():
                    raise Exception(f"{response.json()['error']['status']}: {response.json()['error']['message']}")
            return response
        except Exception as e:
            if any(errorCode in str(e) for errorCode in ['404', '50']):
                continue
            if '429' not in str(e):
                raise Exception(e) from e
            if x == 0:
                print('\nExponential backoff triggered: ')
            x += 1
            if x >= retries:
                print(f'AFTER {retries} ATTEMPTS, THE EXECUTION OF THE FUNCTION FAILED WITH THE EXCEPTION: {e}')
                raise Exception(e) from e
            else:
                sleep = 2 ** x
                print(f'\tError raised: sleeping {sleep} seconds')
                time.sleep(sleep)


def get_request(url: str, headers: dict = None, retries: int = 10) -> dict:
    """GET request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: get(url=url, headers=headers), retries=retries)

def post_request(url: str, headers: dict = None, data: dict = None, retries: int = 10) -> dict:
    """POST request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        data (dict, optional): Request body. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: post(url=url, headers=headers, data=json.dumps(data)), retries=retries)

def put_request(url: str, headers: dict = None, data: dict = None, retries: int = 10) -> dict:
    """PUT request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        data (dict, optional): Request body. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: put(url=url, headers=headers, data=json.dumps(data)), retries=retries)

def delete_request(url: str, headers: dict = None, data: dict = None, retries: int = 10) -> dict:
    """DELETE request with integrated exponential backoff retry strategy

    Args:
        url (str): Request URL
        headers (dict, optional): Request headers. Defaults to None.
        data (dict, optional): Request body. Defaults to None.
        retries (int, optional): Number of retries. Defaults to 10.

    Returns:
        dict: Request response
    """
    return exponential_backoff(func=lambda: delete(url=url, headers=headers, data=json.dumps(data)), retries=retries)
