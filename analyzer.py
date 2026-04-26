import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"


def agrupar_noticias(resultados):

    texto = ""

    for i, r in enumerate(resultados, start=1):
        texto += f"""
Noticia {i}:
Evento: {r['evento'][:120]}
Medio: {r['diario']}
"""

    prompt = f"""
Sos un editor de noticias.

Tenés una lista de noticias que YA pertenecen a la MISMA categoría.

Tu tarea es AGRUPARLAS según si describen el MISMO HECHO puntual.

⚠️ DEFINICIÓN CLAVE:

Dos noticias son el mismo grupo SOLO si:
- describen el mismo evento exacto
- misma situación concreta
- mismo hecho noticioso

NO agrupar:
❌ mismo tema general (ej: economía)
❌ noticias relacionadas pero distintas
❌ análisis o consecuencias

⚠️ REGLAS:
- NO inventar
- NO interpretar de más
- NO forzar agrupaciones
- Si hay duda → NO agrupar

⚠️ PROHIBIDO AGRUPAR:

- no comparten actores principales
- no comparten mismo hecho exacto
- noticias con temas distintos aunque sean de economía

⚠️ IMPORTANTE:
- Cada noticia debe aparecer UNA sola vez
- No repetir índices
- No dejar noticias afuera

⚠️ FORMATO OBLIGATORIO:

GRUPO:
- 1
- 3

GRUPO:
- 2

GRUPO:
- 4
- 5

(No agregar explicaciones, texto extra ni títulos)

---

Noticias:
{texto}
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Agrupás noticias por evento exacto."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 600
    }

    for intento in range(3):
        try:
            print(f"📏 Prompt length: {len(prompt)}")
            print(f"🔁 Intento {intento+1}/3")

            response = requests.post(
                URL,
                headers=headers,
                json=data,
                timeout=(5, 20)
            )

            if response.status_code == 429:
                print("⏳ Rate limit → esperando 10s...")
                time.sleep(10)
                continue

            if response.status_code != 200:
                print("❌ Error:", response.text)
                return None

            return response.json()["choices"][0]["message"]["content"]

        except Exception as e:
            print("⚠️ Error:", e)
            time.sleep(5)

    return None