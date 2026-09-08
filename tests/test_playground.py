import json
import pytest
from unittest.mock import MagicMock, patch
from needle.playground import server

class MockEngine(server.Engine):
    def __init__(self):
        super().__init__()
        self.name = "needle-2 (base)"
        self.weights = None

    def complete(self, tools_json, query, python_code=None, execute=False):
        res = {
            "function_calls": [{"name": "set_lights", "arguments": {"room": "bedroom", "brightness": 20}}],
            "type": "call",
            "confidence": 0.98,
            "decode_tps": 45.2
        }
        if execute:
            res["results"] = self._execute_calls(res, python_code)
        return res

    def reset(self):
        pass

    def load_weights(self, path):
        self.name = "custom.cact"
        self.weights = path

def test_playground_handler_get():
    server._Handler.engine = MockEngine()

    # Static files test
    handler = server._Handler.__new__(server._Handler)
    handler.path = "/index.html"
    sent = []
    handler._send = lambda code, body, ctype="application/json": sent.append((code, body, ctype))
    handler.do_GET()
    assert len(sent) == 1
    assert sent[0][0] == 200
    assert "Needle 2 Playground" in sent[0][1].decode("utf-8")

    # Model info
    sent.clear()
    handler.path = "/model"
    handler.do_GET()
    assert sent[0][0] == 200
    assert json.loads(sent[0][1]) == {"name": "needle-2 (base)"}

    # Finetune status
    sent.clear()
    handler.path = "/finetune/status"
    handler.do_GET()
    assert sent[0][0] == 200
    status = json.loads(sent[0][1])
    assert "running" in status

    # 404
    sent.clear()
    handler.path = "/nonexistent"
    handler.do_GET()
    assert sent[0][0] == 404

def test_playground_handler_post_execution():
    mock_eng = MockEngine()
    server._Handler.engine = mock_eng
    handler = server._Handler.__new__(server._Handler)

    # Complete with real python execution
    sent = []
    py_code = """
def set_lights(room, brightness):
    return f"Set {room} to {brightness}%"
"""
    handler._send = lambda code, body, ctype="application/json": sent.append((code, body, ctype))
    handler._json_body = lambda: {
        "query": "dim lights",
        "tools": "[]",
        "code": py_code,
        "execute": True
    }
    handler.path = "/complete"
    handler.do_POST()
    assert sent[0][0] == 200
    res = json.loads(sent[0][1])
    assert res["function_calls"][0]["name"] == "set_lights"
    assert res["results"][0]["output"] == "Set bedroom to 20%"

    # Reset
    sent.clear()
    handler._json_body = lambda: {}
    handler.path = "/reset"
    handler.do_POST()
    assert sent[0][0] == 200
    assert json.loads(sent[0][1]) == {"ok": True}

def test_cli_version(capsys):
    from needle import cli
    import sys
    with patch.object(sys, "argv", ["needle", "--version"]):
        with pytest.raises(SystemExit) as exc:
            cli.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "cactus-needle 2.0.12" in captured.out
