__version__ = "1.1.0"

from .client import SignalRClient
from .hub_proxy import HubProxy

__all__ = ("SignalRClient", "HubProxy")
