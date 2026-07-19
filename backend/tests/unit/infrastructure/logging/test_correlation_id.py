import asyncio
import contextvars

import pytest
from loguru import logger

from src.infrastructure.logging.loguru_setup import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
)


def test_correlation_id_context_management():
    test_id = "test-correlation-123"
    set_correlation_id(test_id)
    assert get_correlation_id() == test_id

    def new_context():
        assert get_correlation_id() is None
        set_correlation_id("context-456")
        assert get_correlation_id() == "context-456"

    ctx = contextvars.Context()
    ctx.run(new_context)

    assert get_correlation_id() == test_id


def test_generate_correlation_id():
    id1 = generate_correlation_id()
    id2 = generate_correlation_id()

    assert id1 != id2
    assert len(id1) == 36
    assert len(id2) == 36
    assert "-" in id1
    assert "-" in id2


def test_correlation_id_appears_in_log_output_via_patcher(capsys):
    sink_id = logger.add(lambda msg: print(msg, end=""), format="{extra[correlation_id]} - {message}")
    try:
        set_correlation_id("filter-test-789")
        logger.info("Test message with correlation ID")
        captured = capsys.readouterr()
        assert "filter-test-789" in captured.out
        assert "Test message with correlation ID" in captured.out
    finally:
        logger.remove(sink_id)


def test_correlation_id_defaults_to_no_correlation_without_context(capsys):
    sink_id = logger.add(lambda msg: print(msg, end=""), format="{extra[correlation_id]} - {message}")
    try:

        def run_test():
            logger.info("Test message without correlation ID")

        ctx = contextvars.Context()
        ctx.run(run_test)
        captured = capsys.readouterr()
        assert "no-correlation" in captured.out
        assert "Test message without correlation ID" in captured.out
    finally:
        logger.remove(sink_id)


@pytest.mark.asyncio
async def test_correlation_id_isolated_across_concurrent_asyncio_tasks():
    results: dict[int, str | None] = {}

    async def task_function(task_id: int) -> None:
        set_correlation_id(f"task-{task_id}")
        await asyncio.sleep(0)
        results[task_id] = get_correlation_id()

    await asyncio.gather(*(task_function(i) for i in range(5)))

    assert results == {i: f"task-{i}" for i in range(5)}
    assert len(set(results.values())) == 5


def test_correlation_id_multiple_sync_contexts():
    results = {}

    def context_function(context_id):
        test_id = f"context-{context_id}"
        set_correlation_id(test_id)
        results[context_id] = get_correlation_id()

    for i in range(3):
        ctx = contextvars.copy_context()
        ctx.run(context_function, i)

    assert results[0] == "context-0"
    assert results[1] == "context-1"
    assert results[2] == "context-2"
    assert len(set(results.values())) == 3
