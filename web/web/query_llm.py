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


def llm(model=model, input_prompt="Hallo", system_prompt="Du bist ein hilfsbereiter KI-Assisstent", format=''):
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

system_prompt = """
Du bist ein medizinischer Regex-Generator. Wandle Benutzeranfragen über Radiologie-Berichte in JSON-Format um.

Deine Aufgabe:
1. Extrahiere die wichtigsten Informationen aus der Benutzeranfrage
2. Erstelle für den Berichtsstext eine Wildcard Query, die diese Begriffe sucht. Dabei sollen automatisch Buchstabierungsvarianten und Reihenfolgvarianten abgedeckt sein. Schaue, dass die query so gut wie möglich die Benutzeranfrage abbildet und dass du nicht zu viele Pathologien einschliesst (zB bei Hypertension -> einfach *idiopathische*, welches auch viele andere Krankheiten involvieren würde).
3. Erstelle für die Bildgebungsmodalitäten eine Lucene Regex Query, die diese Begriffe sucht. Hier reicht es, wenn die gängigsten Gross- und Kleinschreibvarianten und Buchstabierungsvarianten probiert werden, es muss nicht alles abgedeckt werden sondern nur die häufigsten. Die Query darf nicht länger als 255 Zeichen sein. Es sollen nur deutsche Begriffe für Modalitäten abgedeckt werden.

Ausgabeformat (nur JSON, keine Erklärung):
{
  "bericht_query": *tokenisierte query in SOLR Regex Form*,
  "modality_query": *single-query in SOLR Regex Form*
}

Beispiel 1:
Benutzer: "Alle US untersuchungen Abdomen ohne Biopsie bei Bauchschmerzen"
Ausgabe: {
  "bericht_query": "(*bauchschmerz* OR *bauchweh* OR *oberbauchschmerz* OR *unterbauchschmerz* OR *mittelbauchschmerz* OR *flankenschmerz* OR *leistenschmerz* OR *leistenbeschwerden* OR *abdomenschmerz* OR *abdomin*schmerz* OR *abdomin*beschwerden* OR *epigastr*schmerz* OR *hypogastr*schmerz* OR *nabelschmerz* OR *periumbilik*schmerz* OR *paraumbilik*schmerz* OR *kolik*bauch* OR *kolik*abdom*)",
  "modality_query": "/(.*[sS]onogra(ph|f)?(ie|y)?.*)&(.*[aA]bdom.*)&~(.*[bB]iopsie.*)/",
}

Beispiel 2:
Benutzer: "Alle CT Schädel mit Epiduralblutungen"
Ausgabe: {
  "bericht_query": "("epidural hämatom*"~3 OR "hämatom*epidural"~3 OR "epidural blut*"~3 OR "blut* epidural"~3 OR "extradural hämatom*"~3 OR "hämatom* extradural"~3 OR "extradural blut*"~3 OR "blut* extradural"~3)",
  "modality_query": "/.*CT.*Sch(ä|ae)del.*/",
}
"""

def llm_validate(model="mistral-small3.2:24b-instruct-2506-q8_0", input_prompt="", system_prompt=system_prompt, format=query_output.model_json_schema()):    
    
    try:
        llm_output = llm(input_prompt=input_prompt, system_prompt=system_prompt, format=format)
        llm_output = query_output.model_validate_json(llm_output)
    except:
        try:
            llm_output = query_output.model_validate(json.loads(llm_output))
        except:
            llm_output = None

    return llm_output.model_dump() if llm_output else query_output().model_dump()