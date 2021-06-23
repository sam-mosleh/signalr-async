class ConnectionError(Exception):
    pass


class ConnectionInitializationError(ConnectionError):
    pass


class ConnectionStartError(ConnectionError):
    pass


class IncompatibleServerError(ConnectionError):
    pass


class ServerInvokationException(Exception):
    pass
