# {
#     MessageId: minPersistentResponse.C,
#     Messages: minPersistentResponse.M,
#     Initialized: typeof (minPersistentResponse.S) !== "undefined" ? true : false,
#     ShouldReconnect: typeof (minPersistentResponse.T) !== "undefined" ? true : false,
#     LongPollDelay: minPersistentResponse.L,
#     GroupsToken: minPersistentResponse.G,
#     Error: minPersistentResponse.E
# };

# $(connection).triggerHandler(signalR.events.onError, [signalR._.error(minData.E, /* source */ "ServerError")]);
# if(minData && (typeof minData.I !== "undefined")) $(connection).triggerHandler(events.onReceived, [data]);
# $.each(minData.M, function (index, message) transportLogic.triggerReceived(connection, message);
# I == Completion

# HUB_INVOCATION
# [JsonProperty("H")]
# public string Hub { get; set; }
# [JsonProperty("M")]
# public string Method { get; set; }
# [JsonProperty("I")]
# public string Id { get; set; }
# [JsonProperty("S")]
# public JRaw State { get; set; }
# [JsonProperty("A")]
# public JRaw[] Args { get; set; }

# HUB_RESULT
# /// <summary>
# /// The callback identifier
# /// </summary>
# [JsonProperty("I")]
# public string Id { get; set; }

# /// <summary>
# /// The progress update of the invocation
# /// </summary>
# [JsonProperty("P")]
# public HubProgressUpdate ProgressUpdate { get; set; }

# /// <summary>
# /// The return value of the hub
# /// </summary>
# [JsonProperty("R")]
# public JToken Result { get; set; }

# /// <summary>
# /// Indicates whether the Error is a <see cref="HubException"/>.
# /// </summary>
# [JsonProperty("H")]
# public bool? IsHubException { get; set; }

# /// <summary>
# /// The error message returned from the hub invocation.
# /// </summary>
# [JsonProperty("E")]
# public string Error { get; set; }

# /// <summary>
# /// Extra error data
# /// </summary>
# [JsonProperty("D")]
# public object ErrorData { get; set; }

# /// <summary>
# /// The caller state from this hub.
# /// </summary>
# [SuppressMessage("Microsoft.Usage", "CA2227:CollectionPropertiesShouldBeReadOnly", Justification = "Type is used for serialization.")]
# [JsonProperty("S")]
# public IDictionary<string, JToken> State { get; set; }

# if "P" in message => message: HUB_RESULT
# else if "I" in message => message: HUB_RESULT
# else message: HUB_INVOCATION

import asyncio
from typing import Dict, List, Optional, Any

from signalr_async.client import SignalRClientBase

from .connection import SignalRConnection
from .hub import SignalRHub
from .invoke_manager import SignalRInvokeManager


class SignalRClient(SignalRClientBase[List[SignalRHub]]):
    def build_connection(
        self,
        base_url: str,
        connection_options: Dict[str, Any],
    ) -> SignalRConnection:
        return SignalRConnection(
            base_url=base_url,
            hub_names=[hub.name for hub in self._hub],
            extra_params=connection_options.get("extra_params"),
            extra_headers=connection_options.get("extra_headers"),
            logger=self.logger,
        )

    def build_invoke_manager(self) -> SignalRInvokeManager:
        invoke_manager = SignalRInvokeManager(self._producer_queue)
        for hub in self._hub:
            hub._set_invoke_manager(invoke_manager)._set_logger(self.logger)
        return invoke_manager

    async def _connection_event(self) -> None:
        if self._connection.connection_id:
            for hub in self._hub:
                asyncio.create_task(hub.on_connect(self._connection.connection_id))

    async def _disconnection_event(self) -> None:
        for hub in self._hub:
            asyncio.create_task(hub.on_disconnect())

    def _get_message_id(self, message: Dict[str, Any]) -> str:
        return message["I"]  # type: ignore

    async def _process_message(self, message: Dict[str, Any]) -> None:
        print("MESSAGE", message)
