from typing import Callable

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

        super().__init__(f'{message}{err_code}')

class TooManyRequestsError(HTTPRequestError):
    """Generic exception for HTTP Request Exceptions
        It can receive the function name and the function arguments, besides the message, to better help debugging the error
    """
    def __init__(self, func_name=None, message=None, *args, **kwargs):
        super().__init__(err_code='429 Too Many Requests', func_name=func_name, message=message, *args, **kwargs)

class AccessTokenExpiredError(HTTPRequestError):
    """Exception raised when the SpofifyAPI access token has expired
        It can receive the function name and the function arguments, besides the message, to better help debugging the error
    """
    func: Callable
    args: list
    kwargs: 'dict[str,]'

    def __init__(self, func_name: str = None, func: Callable = None, message: str = None, *args, **kwargs):
        super().__init__(err_code='401 Access Token Expired', func_name=func_name, message=message, *args, **kwargs)
        self.func = func
        self.args = args
        self.kwargs = kwargs
