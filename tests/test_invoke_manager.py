from signalr_async.invoke_manager import InvokeManagerBase
from signalr_async.exceptions import ServerInvocationException
from pytest_mock import MockerFixture
import asyncio
import pytest

pytestmark = pytest.mark.asyncio


class DummyInvokeManager(InvokeManagerBase):
    async def invoke(self, *args, **kwargs):
        pass


def test_invoke_manager_invocation_id_creation():
    manager = DummyInvokeManager(None)
    assert manager.total_invokes == 0
    assert manager._create_invocation_id() == "0"
    assert manager.total_invokes == 1
    assert manager.invocation_events.get("0") is not None
    assert manager.invocation_events.get("1") is None


def test_set_invalid_result_and_exception():
    manager = DummyInvokeManager(None)
    with pytest.raises(RuntimeError):
        manager.set_invocation_result("0", None)
    with pytest.raises(RuntimeError):
        manager.set_invocation_exception("0", None)


async def test_invoke_putting_in_queue(mocker: MockerFixture):
    mock_queue = mocker.AsyncMock()
    manager = DummyInvokeManager(mock_queue)
    invocation_id = manager._create_invocation_id()
    message = mocker.MagicMock()
    task = asyncio.create_task(
        manager._invoke_and_wait_for_result(invocation_id, message)
    )
    await asyncio.sleep(0)
    mock_queue.put.assert_awaited_once_with(message)
    task.cancel()


async def test_invoke_with_result(mocker: MockerFixture):
    mock_queue = mocker.AsyncMock()
    manager = DummyInvokeManager(mock_queue)
    invocation_id = manager._create_invocation_id()
    task = asyncio.create_task(manager._invoke_and_wait_for_result(invocation_id, None))
    await asyncio.sleep(0)
    result = mocker.MagicMock()
    assert task.done() is False
    manager.set_invocation_result(invocation_id, result)
    await asyncio.sleep(0)
    assert task.done()
    assert (await task) == result


async def test_invoke_with_exception(mocker: MockerFixture):
    mock_queue = mocker.AsyncMock()
    manager = DummyInvokeManager(mock_queue)
    invocation_id = manager._create_invocation_id()
    message = mocker.MagicMock()
    task = asyncio.create_task(
        manager._invoke_and_wait_for_result(invocation_id, message)
    )
    await asyncio.sleep(0)
    assert task.done() is False
    error_msg = "error message"
    manager.set_invocation_exception(invocation_id, error_msg)
    with pytest.raises(ServerInvocationException, match=error_msg):
        await task
