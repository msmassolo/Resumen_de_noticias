import os
import time

import requests
from dotenv import load_dotenv


load_dotenv()

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


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

            if response.status_code == 429 and intento < retries:
                espera = 6 * (intento + 1)
                print(f"Rate limit. Esperando {espera}s...")
                time.sleep(espera)
                continue

            if response.status_code != 200:
                print("Error Groq:", response.text[:300])
                return None

            return response.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"Error Groq: {e}")
            if intento < retries:
                time.sleep(4)

    return None
