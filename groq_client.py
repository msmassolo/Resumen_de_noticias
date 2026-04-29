import os
import time

import requests
from dotenv import load_dotenv


load_dotenv()

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def recortar_texto(texto, max_chars):
    texto = " ".join((texto or "").split())
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars].rsplit(" ", 1)[0]


def _api_key():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no esta definida")
    return api_key


def pedir_groq(system_prompt, user_prompt, *, max_tokens=160, temperature=0, retries=2):
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for intento in range(retries + 1):
        try:
            response = requests.post(URL, headers=headers, json=data, timeout=(5, 20))

            if response.status_code in RETRY_STATUS_CODES and intento < retries:
                espera = min(30, 4 * (2 ** intento))
                print(f"Groq {response.status_code}. Reintentando en {espera}s...")
                time.sleep(espera)
                continue

            if response.status_code != 200:
                print(f"Error Groq {response.status_code}:", response.text[:300])
                return None

            try:
                return response.json()["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError, ValueError) as e:
                print(f"Respuesta inesperada de Groq: {e}")
                return None

        except Exception as e:
            print(f"Error Groq: {e}")
            if intento < retries:
                espera = min(30, 4 * (2 ** intento))
                print(f"Reintentando en {espera}s...")
                time.sleep(espera)

    return None
