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


class ServerInvocationException(AsyncSignalRException):
    pass


class MessageError(AsyncSignalRException):
    pass


class InvalidMessage(MessageError):
    pass
