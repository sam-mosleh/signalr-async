import pytest
from pytest_mock import MockFixture

from signalr_async.net.hub import SignalRHub
from signalr_async.net.messages import HubInvocation

pytestmark = pytest.mark.asyncio


async def test_unregistered_signalr_hub_invoke():
    h = SignalRHub()
    with pytest.raises(RuntimeError):
        await h.invoke(None)


async def test_registered_signalr_hub_invoke_message(mocker: MockFixture):
    hub_name = "myhub"
    invocation_id = "1000"
    method = "mymethod"
    args = (1, True)
    hub = SignalRHub(hub_name)
    assert hub._create_invocation_message(invocation_id, method, args) == HubInvocation(
        invocation_id, hub_name, method, args, None
    )
