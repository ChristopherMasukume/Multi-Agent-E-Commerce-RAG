from unittest.mock import Mock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

import agent_orchestrator as ao


def test_retrieves_memory_summaries():
    mock_response = {
        "memoryRecordSummaries": [
            {"content": {"text": "Customer prefers email updates."}},
            {"content": {"text": "Previous order was delayed."}},
        ]
    }

    with patch.object(
        ao.agentcore_client,
        "retrieve_memory_records",
        return_value=mock_response,
    ) as mocked:
        result = ao._retrieve_session_memory(
            "test-memory-id", "CUST-001", "session-123", "Where is my order?"
        )

    assert result == (
        "Customer prefers email updates.\nPrevious order was delayed."
    )
    mocked.assert_called_once_with(
        memoryId="test-memory-id",
        namespacePath="/summaries/CUST-001/session-123",
        searchCriteria={
            "searchQuery": "Where is my order?",
            "topK": 3,
        },
    )
    print("PASS: memory summaries are retrieved correctly")


def test_retrieval_failure_is_safe():
    with patch.object(
        ao.agentcore_client,
        "retrieve_memory_records",
        side_effect=RuntimeError("simulated AWS failure"),
    ):
        result = ao._retrieve_session_memory(
            "test-memory-id", "CUST-001", "session-123", "order status"
        )

    assert result == ""
    print("PASS: retrieval failure returns an empty context")


def test_records_user_event():
    with patch.object(ao.agentcore_client, "create_event") as mocked:
        ao._record_memory_event(
            "test-memory-id", "CUST-001", "session-123", "USER",
            "Where is my order?",
        )

    mocked.assert_called_once()
    event = mocked.call_args.kwargs

    assert event["memoryId"] == "test-memory-id"
    assert event["actorId"] == "CUST-001"
    assert event["sessionId"] == "session-123"
    assert event["payload"][0]["conversational"]["role"] == "USER"
    assert (
        event["payload"][0]["conversational"]["content"]["text"]
        == "Where is my order?"
    )
    print("PASS: user event is recorded with the correct identifiers")


def test_empty_inputs_skip_aws_calls():
    with (
        patch.object(ao.agentcore_client, "retrieve_memory_records") as retrieve,
        patch.object(ao.agentcore_client, "create_event") as create,
    ):
        assert ao._retrieve_session_memory(
            "", "CUST-001", "session-123", "order status"
        ) == ""
        ao._record_memory_event(
            "", "CUST-001", "session-123", "USER", "Hello"
        )
        ao._record_memory_event(
            "test-memory-id", "CUST-001", "session-123", "USER", ""
        )

    retrieve.assert_not_called()
    create.assert_not_called()
    print("PASS: empty inputs do not call AWS")


if __name__ == "__main__":
    tests = [
        test_retrieves_memory_summaries,
        test_retrieval_failure_is_safe,
        test_records_user_event,
        test_empty_inputs_skip_aws_calls,
    ]

    for test in tests:
        test()

    print(f"\nAll {len(tests)} memory helper tests passed.")
