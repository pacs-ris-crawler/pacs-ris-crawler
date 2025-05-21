from ollama import Client
from pydantic import BaseModel, Field
from typing import List
import json
from flask import current_app

# model = "llama3.3:70b-instruct-q5_K_M"
# model = mixtral:8x7b-instruct-v0.1-q8_0
model = "mistral-small:24b-instruct-2501-q4_K_M"
# model = mistral-small3.1:24b-instruct-2503-fp16
# model = "mistral-small3.1:24b-instruct-2503-q8_0"

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

    regex_pattern: str = Field(..., title="Regex", description="best regex pattern to search through the database")
    study_description: List[str] = Field(..., title="StudyDescriptions", description="a list of all study descriptions to be looked for")
    phrases: List[str] = Field(..., title="Phrases", description="different word phrases to be used for search which are covered by the regex pattern")

system_prompt = (
    "Du bist ein medizinischer Regex-Spezialist. Deine Aufgabe ist es, frei formulierte menschliche Suchanfragen "
    "in **radiologischen Berichten** in präzise, PCRE-kompatible reguläre Ausdrücke zu übersetzen.\n\n"
    "### Kontext der Berichte\n"
    "Jeder Bericht besteht aus genau fünf Abschnitten mit festen Labels: Anamnese, Fragestellung, Technik, Befund, Beurteilung.\n\n"
    "### Vorgehen\n"
    "1. **Abschnitte wählen**: Entscheide, in welchen der fünf Abschnitte gesucht werden soll – es können auch mehrere Abschnitte sein.\n"
    "2. **Phrasen ableiten**: Erzeuge aus der Anfrage relevante Suchphrasen und gängige Synonyme.\n"
    "3. **Regex bauen**: Generiere genau einen Ausdruck, der folgende Eigenschaften hat:\n"
    "   • **Abschnitts-Anchor** am Zeilenanfang (case-insensitive, z. B. `(?mi)^Label:`) – ohne diesen darf kein Treffer entstehen.\n"
    "   • **Multiline-Support**: Erlaube mit DOTALL (`(?s)`) oder expliziten Zeilenumbruchs-Tokens (`\\r?\\n`), dass der Ausdruck "
    "über mehrere Zeilen sucht.\n"
    "   • **Nicht-gierige Quantifizierung** (`.*?`), damit nach dem Header nur bis zum ersten echten Vorkommen deiner Phrasen eingespannt wird.\n"
    "   • **Phrasen-Gruppe** als ODER-Konstruktion mit Wortgrenzen (`\\b(?:…|…)\\b`), die zwingend mindestens eine Phrase enthalten muss.\n"
    "   • **Kein Match**, wenn nur der Abschnitts-Anchor existiert – es muss immer wirklich eine der Phrasen folgen.\n"
    "4. **Flags & Technik**: Nutze case-insensitive (`(?i)`) und ggf. DOTALL-Modus (`(?s)`), vermeide variable-length Lookbehinds.\n\n"
    "### Ausgabeformat (JSON)\n"
    "Antwort nur mit diesem Objekt, ohne zusätzlichen Text:\n"
    "{\n"
    "  \"phrases\": [\"<Liste_der_Suchphrasen>\"],\n"
    "  \"regex_pattern\": \"<vollständiges_PCRE_Muster>\"\n"
    "}\n\n"
    "Antworte auf Deutsch."
)

def llm_dummy(model=model, input_prompt="Bauchschmerzen", system_prompt=system_prompt, format=query_output.model_json_schema()):
    
    try:
        llm_output = llm(input_prompt=input_prompt, system_prompt=system_prompt, format=format)
        llm_output = query_output.model_validate_json(llm_output)
    except:
        try:
            llm_output = query_output.model_validate(json.loads(llm_output))
        except:
            llm_output = None

    return llm_output.model_dump() if llm_output else query_output().model_dump()


# print(llm_dummy(input=input_prompt, system_prompt=system_prompt))

