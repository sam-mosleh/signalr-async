class AsyncSignalRException(Exception):
    pass


class AsyncSignalRConnectionError(AsyncSignalRException, ConnectionError):
    pass


class ConnectionInitializationError(AsyncSignalRConnectionError):
    pass


class HandshakeError(ConnectionInitializationError):
    pass


class IncompatibleServerError(AsyncSignalRConnectionError):
    pass


class ConnectionClosed(AsyncSignalRConnectionError):
    pass


class ServerInvokationException(AsyncSignalRException):
    pass
