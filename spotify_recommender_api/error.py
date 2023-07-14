from typing import Callable, Union, Any

class HTTPRequestError(Exception):
    """Generic exception for HTTP Request Exceptions
        It can receive the error code and function name, and the function arguments, besides the message, to better help debugging the error
    """
    def __init__(
        self,
        message=None,
        err_code=None,
        func_name=None,
        *args,
        **kwargs
    ):
        if func_name:
            arguments = ", ".join(args)
            if kwargs:
                if args:
                    arguments += ", "
                arguments += ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            if message is None:
                message = 'There was an error regarding an HTTP Request'

            message += f', on the execution of the {func_name}({arguments}) function'

        err_code = f': {err_code}' if err_code else ''

        self.message = f'{message}{err_code}'

        super().__init__(self.message)

class TooManyRequestsError(HTTPRequestError):
    """Generic exception for HTTP Request Exceptions
        It can receive the function name and the function arguments, besides the message, to better help debugging the error
    """
    def __init__(self, func_name=None, message=None, *args, **kwargs):
        super().__init__(*args, err_code='429 Too Many Requests', func_name=func_name, message=message, **kwargs)

class AccessTokenExpiredError(HTTPRequestError):
    """Exception raised when the SpofifyAPI access token has expired
        It can receive the function name and the function arguments, besides the message, to better help debugging the error
    """
    func: Union[Callable, None]
    args: 'tuple[Any]'
    kwargs: 'dict[str, Any]'

    def __init__(self, func_name: Union[str, None] = None, func: Union[Callable, None] = None, message: Union[str, None] = None, *args, **kwargs):
        super().__init__(*args, err_code='401 Access Token Expired', func_name=func_name, message=message, **kwargs)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __str__(self) -> str:
        return 'Access Token is not valid'

class EmptyResultError(Exception):
    """Exception raised when the result from an operation is empty, such as a dataframe when the filter of a specific artist is applied

    """
    def __init__(self, message: str) -> None:
        super().__init__(message)

class NoPlaylistProvidedError(Exception):
    """Exception raised when trying to access a playlist action without have provided a playlist beforehand

    """
    def __init__(self, message: str) -> None:
        super().__init__(message)