import pytest
from pytest_mock import MockFixture

from signalr_async.netcore.hub import SignalRCoreHub
from signalr_async.netcore.messages import InvocationMessage

pytestmark = pytest.mark.asyncio


async def test_unregistered_signalrcore_hub_invoke():
    h = SignalRCoreHub()
    with pytest.raises(RuntimeError):
        await h.invoke(None)


async def test_registered_signalrcore_hub_invoke_message(mocker: MockFixture):
    invocation_id = "1000"
    method = "mymethod"
    args = (1, True)
    hub = SignalRCoreHub()
    assert hub._create_invocation_message(
        invocation_id, method, args
    ) == InvocationMessage(invocation_id, method, args, {}, tuple())
