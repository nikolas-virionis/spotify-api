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