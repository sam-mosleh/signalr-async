import pytest
from pytest_mock import MockFixture

from signalr_async.signalr.hub import SignalRHub

pytestmark = pytest.mark.asyncio


async def test_unregistered_signalr_hub_invoke():
    h = SignalRHub()
    with pytest.raises(RuntimeError):
        await h.invoke(None)


async def test_registered_signalr_hub_invoke(mocker: MockFixture):
    hub_name = "myhub"
    method = "mymethod"
    args = (1, True)
    invoke_manager = mocker.AsyncMock()
    h = SignalRHub(hub_name)._set_invoke_manager(invoke_manager)
    await h.invoke(method, *args)
    invoke_manager.invoke.assert_awaited_once_with(hub_name, method, args)
