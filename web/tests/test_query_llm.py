import json
import unittest
from unittest.mock import MagicMock, patch

from web.app import app
from web.query_llm import (
    get_vllm_base_url,
    get_vllm_model,
    llm_validate,
    load_system_prompt,
    normalize_bericht_query,
    query_output,
)


class TestLlmConfig(unittest.TestCase):
    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_get_vllm_model_from_config(self):
        self.assertEqual(get_vllm_model(), app.config["VLLM_MODEL"])

    def test_get_vllm_model_override(self):
        self.assertEqual(get_vllm_model("custom-model"), "custom-model")

    def test_get_vllm_base_url_from_config(self):
        self.assertEqual(get_vllm_base_url(), app.config["VLLM_URL"].rstrip("/"))


class TestLoadSystemPrompt(unittest.TestCase):
    def test_load_system_prompt_includes_massnahmen(self):
        prompt = load_system_prompt()
        self.assertIn("<role>", prompt)
        self.assertIn("</massnahmen_catalog>", prompt)
        self.assertIn("CT Schädel med. REA", prompt)
        self.assertIn("bericht_query", prompt)


class TestQueryLlmPostProcessing(unittest.TestCase):
    def test_normalize_quotes_multiword_proximity(self):
        raw = "beurteilung* appendicitis~100"
        self.assertEqual(
            normalize_bericht_query(raw),
            '"beurteilung* appendicitis"~100',
        )

    def test_normalize_preserves_or_and(self):
        raw = 'foo bar~3 OR baz qux~5 AND NOT kein test~2'
        normalized = normalize_bericht_query(raw)
        self.assertIn(" OR ", normalized)
        self.assertIn(" AND NOT ", normalized)
        self.assertEqual(normalized.count('"'), 6)

    def test_normalize_collapses_whitespace(self):
        self.assertEqual(
            normalize_bericht_query("  foo   bar~3  "),
            '"foo bar"~3',
        )


class TestLlmValidate(unittest.TestCase):
    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch("web.query_llm.llm")
    def test_llm_validate_postprocesses_response(self, mock_llm):
        mock_llm.return_value = json.dumps(
            {
                "bericht_query": '+"beurteilung* emphysem*"~100 -"kein* *emphysem*"~5',
                "modality_query": "/.*CT.*[tT]horax.*/",
            }
        )

        result = llm_validate(input_prompt="Emphysem Lunge CT Thorax")

        self.assertIn('"beurteilung* emphysem*"~100', result["bericht_query"])
        self.assertEqual(result["modality_query"], "/.*CT.*[tT]horax.*/")

    @patch("web.query_llm.llm")
    def test_llm_validate_returns_empty_on_failure(self, mock_llm):
        mock_llm.return_value = "Error: connection refused"

        result = llm_validate(input_prompt="anything")

        self.assertEqual(result, query_output().model_dump())


class TestVllmRequest(unittest.TestCase):
    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch("web.query_llm._create_client")
    def test_vllm_request_structured_output(self, mock_create_client):
        from web.query_llm import vllm_request

        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "bericht_query": "foo",
                "modality_query": "bar",
            }
        )

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_create_client.return_value = mock_client

        result = vllm_request(
            system_prompt="system",
            user_prompt="user",
            schema=query_output,
        )

        self.assertEqual(result["bericht_query"], "foo")
        self.assertEqual(result["modality_query"], "bar")
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], app.config["VLLM_MODEL"])
