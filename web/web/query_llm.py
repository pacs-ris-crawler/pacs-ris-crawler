import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from flask import current_app
from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).resolve().parent
_SYSTEM_PROMPT_FILE = _PROMPT_DIR / "system_prompt.txt"
_MASSNAHMEN_FILE = _PROMPT_DIR / "massnahmen.txt"

# Safety net: quote unquoted multi-word proximity/boost targets
_PROX_FIX = re.compile(
    r'(?<!")(?!\b(?:OR|AND|NOT)\b)(\b[a-zA-ZäöüÄÖÜß*]+(?:\s+(?!\b(?:OR|AND|NOT)\b)[a-zA-ZäöüÄÖÜß*]+)+)\s*~\s*(\d+)'
)
_BOOST_FIX = re.compile(
    r'(?<!")(?!\b(?:OR|AND|NOT)\b)(\b[a-zA-ZäöüÄÖÜß*]+(?:\s+(?!\b(?:OR|AND|NOT)\b)[a-zA-ZäöüÄÖÜß*]+)+)\s*\^\s*(\d+)'
)


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    prompt = _SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    massnahmen = _MASSNAHMEN_FILE.read_text(encoding="utf-8").strip()
    if massnahmen:
        prompt = f"{prompt.rstrip()}\n{massnahmen}\n</massnahmen_catalog>"
    else:
        prompt = f"{prompt.rstrip()}\n</massnahmen_catalog>"
    return prompt


def normalize_bericht_query(q: str) -> str:
    q = _PROX_FIX.sub(r'"\1"~\2', q)
    q = _BOOST_FIX.sub(r'"\1"^\2', q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def get_vllm_model(model=None) -> str:
    if model:
        return model
    return current_app.config["VLLM_MODEL"]


def get_vllm_base_url() -> str:
    url = current_app.config["VLLM_URL"].rstrip("/")
    if url and not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


def get_vllm_api_key() -> str:
    return current_app.config.get("VLLM_API_KEY", "token-unused")


def _create_client() -> OpenAI:
    return OpenAI(
        base_url=get_vllm_base_url(),
        api_key=get_vllm_api_key(),
    )


def vllm_request(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    *,
    thinking: bool = False,
    schema: type[BaseModel] | None = None,
) -> dict | str:
    client = _create_client()
    model = get_vllm_model(model)

    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 1e-4,
        }

        if thinking:
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": True},
            }

        if schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            }

        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""

        if schema is not None:
            parsed = json.loads(content)
            if thinking:
                reasoning = getattr(response.choices[0].message, "reasoning", None)
                if reasoning:
                    parsed["thinking"] = reasoning
            return parsed

        return content
    except Exception as exc:
        logger.exception("vLLM request failed")
        return f"Error: {exc}"


def llm(
    model=None,
    input_prompt="Hallo",
    system_prompt=None,
    format="",
):
    if system_prompt is None:
        system_prompt = load_system_prompt()

    schema = query_output if format else None
    result = vllm_request(
        system_prompt=system_prompt,
        user_prompt=input_prompt,
        model=get_vllm_model(model),
        thinking=False,
        schema=schema,
    )

    if isinstance(result, dict):
        result.pop("thinking", None)
        return json.dumps(result, ensure_ascii=False)

    return str(result)


class query_output(BaseModel):
    bericht_query: str = Field(default="")
    modality_query: str = Field(default="")


def _postprocess_output(parsed: query_output) -> query_output:
    parsed.bericht_query = normalize_bericht_query(parsed.bericht_query)
    parsed.bericht_query = parsed.bericht_query.replace("'", '"')
    parsed.modality_query = parsed.modality_query.strip()
    return parsed


def llm_validate(
    model=None,
    input_prompt="",
    system_prompt=None,
    format=query_output.model_json_schema(),
):
    if system_prompt is None:
        system_prompt = load_system_prompt()

    llm_output = None
    raw_response = ""
    resolved_model = get_vllm_model(model)

    try:
        raw_response = llm(
            model=resolved_model,
            input_prompt=input_prompt,
            system_prompt=system_prompt,
            format=format,
        )
        llm_output = _postprocess_output(query_output.model_validate_json(raw_response))
    except Exception:
        logger.exception("Failed to parse LLM JSON output")
        try:
            llm_output = _postprocess_output(
                query_output.model_validate(json.loads(raw_response))
            )
        except Exception:
            llm_output = None

    return llm_output.model_dump() if llm_output else query_output().model_dump()
