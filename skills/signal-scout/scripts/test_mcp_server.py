#!/usr/bin/env python3
"""Tests for the MCP server's model-call loop (mcp-server/server.py::_complete)
with the Anthropic client replaced by a fake. No network, no API key.

The daily call cap counts metered calls and is the server's only spend limit,
so every call the API billed has to be metered, including the ones whose
output then turns out to be unusable.
"""

from __future__ import annotations

import json
import types
import unittest
from unittest import mock

from test_people_filter import load_server


def response(stop_reason: str, text: str = "", output_tokens: int = 100) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=None,
        content=[types.SimpleNamespace(type="text", text=text)] if text else [],
        usage=types.SimpleNamespace(
            input_tokens=1000, output_tokens=output_tokens,
            cache_read_input_tokens=0, cache_creation_input_tokens=0,
        ),
    )


class FakeClient:
    def __init__(self, *responses):
        self._responses = list(responses)
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ModelCallMeteringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def call(self, *responses, tool: str = "classify_and_score"):
        """Run one tool call against canned API responses. Returns
        (result or raised exception, list of metered usage records)."""
        metered: list[dict] = []

        def record_call(**kwargs):
            metered.append(kwargs)
            return 0.01

        def finish(analysis, usage, **kwargs):
            record_call(usage=usage, **kwargs)
            return {"ok": True}

        with mock.patch.object(self.server, "_client", lambda: FakeClient(*responses)), \
                mock.patch.object(self.server, "record_call", record_call), \
                mock.patch.object(self.server, "calls_today", lambda: 0), \
                mock.patch.object(self.server, "_finish_run", finish):
            try:
                if tool == "classify_and_score":
                    findings = [{"source_url": "https://example.com/t", "evidence": "e"}]
                    result = self.server.classify_and_score("https://p.example", findings)
                else:
                    result = self.server.find_first_customers("https://p.example")
            except Exception as exc:  # noqa: BLE001 - the test inspects it
                result = exc
        return result, metered

    def test_output_cut_off_at_max_tokens_is_metered_and_named(self):
        result, metered = self.call(response("max_tokens", '{"title": "T", "segments": [{"na', output_tokens=16000))
        self.assertIsInstance(result, RuntimeError)
        self.assertNotIsInstance(result, json.JSONDecodeError)
        self.assertIn("max_tokens", str(result))
        self.assertEqual(len(metered), 1)
        self.assertEqual(metered[0]["usage"].output_tokens, 16000)
        self.assertEqual(metered[0]["product_url"], "https://p.example")

    def test_refusal_is_metered(self):
        result, metered = self.call(response("refusal"))
        self.assertIsInstance(result, RuntimeError)
        self.assertEqual(len(metered), 1)

    def test_unparseable_output_is_metered(self):
        result, metered = self.call(response("end_turn", "Here is the analysis you asked for."))
        self.assertIsInstance(result, Exception)
        self.assertEqual(len(metered), 1)

    def test_research_loop_that_never_finishes_is_metered_for_every_turn(self):
        turns = [response("pause_turn") for _ in range(self.server.MAX_PAUSE_TURNS + 1)]
        result, metered = self.call(*turns, tool="find_first_customers")
        self.assertIsInstance(result, RuntimeError)
        self.assertEqual(len(metered), 1)
        self.assertEqual(metered[0]["usage"].input_tokens, 1000 * len(turns))

    def test_api_error_after_a_billed_turn_is_metered(self):
        result, metered = self.call(response("pause_turn"), ConnectionError("dropped"), tool="find_first_customers")
        self.assertIsInstance(result, ConnectionError)
        self.assertEqual(len(metered), 1)
        self.assertEqual(metered[0]["usage"].input_tokens, 1000)

    def test_api_error_before_any_response_is_not_metered(self):
        result, metered = self.call(ConnectionError("no route"))
        self.assertIsInstance(result, ConnectionError)
        self.assertEqual(metered, [])

    def test_successful_call_is_metered_once(self):
        result, metered = self.call(response("end_turn", json.dumps({"title": "T"})))
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(metered), 1)


if __name__ == "__main__":
    unittest.main()
