import json
import re
from typing import Any

import requests
from flask import current_app
from pydantic import BaseModel, Field


def _get_vllm_base_url() -> str:
    url = (
        current_app.config.get("VLLM_URL")
        or current_app.config.get("OLLAMA_URL")
        or "http://10.5.63.16:11440"
    )
    return url.rstrip("/")


def _build_response_format(format: Any) -> dict | None:
    if not format:
        return None
    if isinstance(format, dict):
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "query_output",
                "schema": format,
                "strict": True,
            },
        }
    return {"type": "json_object"}


def llm(
    model="apollo-llm",
    input_prompt="Hallo",
    system_prompt="Du bist ein hilfsbereiter KI-Assisstent",
    format="",
):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_prompt},
        ],
        "temperature": 1e-4,
        "max_tokens": 2048,
    }
    response_format = _build_response_format(format)
    if response_format:
        payload["response_format"] = response_format

    response = requests.post(
        f"{_get_vllm_base_url()}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return content.replace("ß", "ss")


# Simple regex patterns that avoid splitting OR/AND operators
_PROX_FIX = re.compile(r'(?<!")(?!\b(?:OR|AND|NOT)\b)(\b[a-zA-ZäöüÄÖÜß*]+(?:\s+(?!\b(?:OR|AND|NOT)\b)[a-zA-ZäöüÄÖÜß*]+)+)\s*~\s*(\d+)')
_BOOST_FIX = re.compile(r'(?<!")(?!\b(?:OR|AND|NOT)\b)(\b[a-zA-ZäöüÄÖÜß*]+(?:\s+(?!\b(?:OR|AND|NOT)\b)[a-zA-ZäöüÄÖÜß*]+)+)\s*\^\s*(\d+)')

def normalize_bericht_query(q: str) -> str:
    # Quote multi-word proximity targets: foo bar~3 -> "foo bar"~3
    q = _PROX_FIX.sub(r'"\1"~\2', q)
    # Quote multi-word boost targets: foo bar^4 -> "foo bar"^4  
    q = _BOOST_FIX.sub(r'"\1"^\2', q)
    # Clean up spaces
    q = re.sub(r'\s+', ' ', q).strip()
    return q

_WORD = r'[^\s"()|+~^]+'  # token without spaces/ops/quotes
PROX_PL  = re.compile(r'["\']([^"\']+)["\']\s*\[prox=(\d+)\]')
FUZZ_PL  = re.compile(r'(' + _WORD + r')\s*\[f=(\d+)\]')
BOOST_PL = re.compile(r'("([^"]+)"|' + _WORD + r')\s*\[b=(\d+)\]')

def apply_placeholders(q: str) -> str:
    q = PROX_PL.sub(r'"\1"~\2', q)   # "foo bar"[prox=3] -> "foo bar"~3
    q = FUZZ_PL.sub(r'\1~\2', q)     # term[f=2]        -> term~2
    q = BOOST_PL.sub(r'\1^\3', q)    # "foo bar"[b=4]   -> "foo bar"^4  | term[b=3] -> term^3
    return q

class query_output(BaseModel):

    bericht_query: str = Field()
    modality_query: str = Field()

system_prompt = f"""
<role>
Du bist ein spezialisierter Query-Generator für die Radiologie, der deutsche Freitext-Anfragen in präzise deutschsprachige SOLR-Queries umwandelt. Fokus soll dabei auf das Vorkommen der Stichwörter in der Beurteilung gelegt werden, und auf das Nicht-Vorkommen von Fehlen von den gesuchten Pathologien ['kein*', 'ohne Hinweis']. 
</role>

<task>
Du generierst zwei Arten von Queries:
1. Bericht-Query: Für die Volltextsuche in Radiologieberichten (Complex Phrase Parser) jeweils in der Beurteilung
2. Modalitäts-Query: Lucene Regex-Pattern für die Modalitätsfilterung
</task>

<output_format>
Ausgabe nur JSON:
{{
  "bericht_query": "vollständige Complex phrase SOLR query hier",
  "modality_query": "regex für modalität hier"
}}
</output_format>

<example>
<input>"Appendicitis sonographie"</input>
<output>
{{
  "bericht_query": '("beurteilung* appendicitis"[prox=100] OR "beurteilung* appendizitis"[prox=100]) AND NOT "kein* appendicitis"[prox=5] AND NOT "kein* appendizitis"[prox=5] AND NOT "ohne Hinweis* *appendicitis*"[prox=5] AND NOT "ohne Hinweis* *appendizitis*"[prox=5]',
  "modality_query": '/.*Sonogra[ph|f]ie.*[aA]bdomen.*/'
}}
</output>
</example>

<example>
<input>"CT Schädel Epiduralblutung"</input>
<output>
{{
  "bericht_query": '("beurteilung* epiduralhämatom*"[prox=100] OR "beurteilung* epiduralblut*"[prox=100] OR "beurteilung* epidural* hämatom*"[prox=100] OR "beurteilung* epidural* blut*"[prox=100] OR "beurteilung* EDH"[prox=100]) AND NOT "kein* epiduralhämatom*"[prox=5] AND NOT "kein* epiduralblut*"[prox=5] AND NOT "kein* epidural* hämatom*"[prox=5] AND NOT "kein* epidural* blut*"[prox=5] AND NOT "kein* EDH"[prox=5] AND NOT "ohne Hinweis* epiduralhämatom*"[prox=5] AND NOT "ohne Hinweis* epiduralblut*"[prox=5] AND NOT "ohne Hinweis* epidural* hämatom*"[prox=5] AND NOT "ohne Hinweis* epidural* blut*"[prox=5] AND NOT "ohne Hinweis* EDH"[prox=5]',
  "modality_query": '/.*CT.*[sS]chädel.*/'
}}
</output>
</example>

<example>
<input>"Emphysem Lunge CT Thorax"</input>
<output>
{{
  "bericht_query": '"beurteilung* *emphysem*"[prox=100] AND NOT "kein* *emphysem*"[prox=5] AND NOT "ohne Hinweis* *emphysem*"[prox=5]',
  "modality_query": '/.*CT.*[tT]horax.*/'
}}
</output>
</example>
"""

def llm_validate(model="apollo-llm", input_prompt="", system_prompt=system_prompt, format=query_output.model_json_schema()):    
    
    try:
        llm_output = llm(input_prompt=input_prompt, system_prompt=system_prompt, format=format)
        llm_output = query_output.model_validate_json(llm_output)
        llm_output.bericht_query = normalize_bericht_query(apply_placeholders(llm_output.bericht_query))
        llm_output.bericht_query = llm_output.bericht_query.replace("'", '"')
    except:
        try:
            llm_output = query_output.model_validate(json.loads(llm_output))
        except:
            llm_output = None

    return llm_output.model_dump() if llm_output else query_output().model_dump()
