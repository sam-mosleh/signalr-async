from signalr_async.signalrcore.hub import SignalRCoreHub
import pytest
from pytest_mock import MockFixture

pytestmark = pytest.mark.asyncio


async def test_unregistered_signalrcore_hub_invoke():
    h = SignalRCoreHub()
    with pytest.raises(RuntimeError):
        await h.invoke(None)


async def test_registered_signalrcore_hub_invoke(mocker: MockFixture):
    method = "mymethod"
    args = (1, True)
    invoke_manager = mocker.AsyncMock()
    h = SignalRCoreHub()._set_invoke_manager(invoke_manager)
    await h.invoke(method, *args)
    invoke_manager.invoke.assert_awaited_once_with(method, args)
