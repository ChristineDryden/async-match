from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server.chat as chat


class FakeResponses:
    def __init__(self):
        self.calls = []
        self.round = 0

    def create(self, **kwargs):
        snapshot = dict(kwargs)
        snapshot["input"] = list(kwargs.get("input") or [])
        self.calls.append(snapshot)
        assert "previous_response_id" not in snapshot, snapshot
        self.round += 1
        if self.round == 1:
            item = SimpleNamespace(
                type="function_call",
                call_id="call_1",
                name="get_league_summary",
                arguments="{}",
            )
            return SimpleNamespace(id="resp_1", output=[item], output_text="")
        msg = SimpleNamespace(
            type="message",
            content=[SimpleNamespace(type="output_text", text="Melo 领先")],
        )
        return SimpleNamespace(id="resp_2", output=[msg], output_text="Melo 领先")


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_tool_loop_does_not_use_previous_response_id(monkeypatch=None):
    fake = FakeClient()
    original_client = chat._client
    original_call = chat.call_tool
    chat._client = lambda: fake
    chat.call_tool = lambda name, args: '{"leaders":[{"player":"Melo"}]}'
    try:
        result = chat.run_chat("现在谁领先？")
    finally:
        chat._client = original_client
        chat.call_tool = original_call
    assert result["reply"] == "Melo 领先"
    assert len(fake.responses.calls) == 2
    second_input = fake.responses.calls[1]["input"]
    types = [item.get("type") or item.get("role") for item in second_input]
    assert "function_call" in types
    assert "function_call_output" in types
    assert fake.responses.calls[1].get("store") is False


def test_history_is_sent_instead_of_response_id():
    fake = FakeClient()
    original_client = chat._client
    chat._client = lambda: fake
    original_call = chat.call_tool
    chat.call_tool = lambda name, args: "{}"
    try:
        chat.run_chat(
            messages=[
                {"role": "user", "content": "谁领先"},
                {"role": "assistant", "content": "Melo"},
                {"role": "user", "content": "他近5场呢"},
            ]
        )
    finally:
        chat._client = original_client
        chat.call_tool = original_call
    first_input = fake.responses.calls[0]["input"]
    assert first_input[0]["role"] == "user"
    assert first_input[-1]["content"] == "他近5场呢"
    assert "previous_response_id" not in fake.responses.calls[0]


if __name__ == "__main__":
    test_tool_loop_does_not_use_previous_response_id()
    print("ok test_tool_loop_does_not_use_previous_response_id")
    test_history_is_sent_instead_of_response_id()
    print("ok test_history_is_sent_instead_of_response_id")
