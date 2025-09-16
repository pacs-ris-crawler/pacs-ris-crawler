from ollama import Client
from pydantic import BaseModel, Field
from typing import List
import json
from flask import current_app
import re

def create_client():
    def _get_ollama_url():
        return current_app.config.get('OLLAMA_URL', '')
    
    ollama_url = _get_ollama_url()

    client = Client(
        host=ollama_url,
        headers={
            "Content-Type": "application/json"}
        )
    
    return client

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

def llm(model="mistral-small3.2:24b-instruct-2506-q8_0", input_prompt="Hallo", system_prompt="Du bist ein hilfsbereiter KI-Assisstent", format=''):
    client = create_client()
    response = client.generate(
        model=model, 
        system=system_prompt,
        prompt=input_prompt,
        options={
            'temperature': 1e-4,
            'num_ctx': 2048
            },
        format=format
    )

    final_response = response["response"].replace("ß", "ss")  
    return final_response

class query_output(BaseModel):

    bericht_query: str = Field()
    modality_query: str = Field()

system_prompt = f"""
<role>
Du bist ein spezialisierter Query-Generator für die Radiologie, der deutsche Freitext-Anfragen in präzise deutschsprachige SOLR-Queries umwandelt.
</role>

<task>
Du generierst zwei Arten von Queries:
1. Bericht-Query: Für die Volltextsuche in Radiologieberichten (Complex Phrase Parser)
2. Modalitäts-Query: Regex-Pattern für die Modalitätsfilterung
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
  "bericht_query": '"appendicitis" OR "appendizitis" AND NOT "keine appendicitis"[prox=2] AND NOT "keine appendizitis"[prox=2]',
  "modality_query": '/.*Sonogra[ph|f]ie.*[aA]bdomen.*/'
}}
</output>
</example>

<example>
<input>"CT Schädel Epiduralblutung"</input>
<output>
{{
  "bericht_query": '"epiduralhämatom*" OR "epiduralblut*" OR "epidural* hämatom*" OR "epidural* blut*" OR "EDH"',
  "modality_query": '/.*CT.*[sS]chädel.*/'
}}
</output>
</example>

<example>
<input>"Emphysem Lunge CT Thorax"</input>
<output>
{{
  "bericht_query": '"*emphysem*" AND NOT "kein* *emphysem*"[prox=2]',
  "modality_query": '/.*CT.*[tT]horax.*/'
}}
</output>
</example>
"""

def llm_validate(model="mistral-small3.2:24b-instruct-2506-q8_0", input_prompt="", system_prompt=system_prompt, format=query_output.model_json_schema()):    
    
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