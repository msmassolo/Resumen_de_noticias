import logging
import os
import time

import requests
from dotenv import load_dotenv

from scrapers.utils import recortar_en_limite_natural as recortar_texto

logger = logging.getLogger(__name__)

load_dotenv()

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


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
                logger.warning("Groq %s. Reintentando en %ss...", response.status_code, espera)
                time.sleep(espera)
                continue

            if response.status_code != 200:
                logger.error("Error Groq %s: %s", response.status_code, response.text[:300])
                return None

            try:
                return response.json()["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError, ValueError) as e:
                logger.error("Respuesta inesperada de Groq: %s", e)
                return None

        except Exception as e:
            logger.error("Error Groq: %s", e)
            if intento < retries:
                espera = min(30, 4 * (2 ** intento))
                logger.warning("Reintentando en %ss...", espera)
                time.sleep(espera)

    return None
