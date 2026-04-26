import os
import requests
import time
from dotenv import load_dotenv

# 🔥 Cargar variables
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("❌ GROQ_API_KEY no está definida (ni en .env ni en GitHub Secrets)")

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"


def unificar_bloques(texto):

    prompt = f"""
Sos un editor de noticias.

Recibís un grupo de noticias del MISMO evento.

Tu tarea es SOLO redactar el resultado final.

INPUT:
{texto}

⚠️ REGLAS OBLIGATORIAS (NO ROMPER):

- NO inventar links
- NO escribir texto adicional
- NO explicar nada
- NO usar markdown (**)
- NO repetir categorías
- NO agregar frases como "Después de analizar..."

⚠️ SOLO USAR:
- los eventos dados
- los links dados

⚠️ SI NO PODÉS HACERLO → devolver vacío

---

Tareas:

1. Crear un TITULO claro del evento
2. Crear un RESUMEN breve (Max 5 lineas)
3. Incluir EXACTAMENTE los links dados

---

FORMATO EXACTO:

TITULO: ...
RESUMEN: ...
LINKS:
- link
- link

(SIN texto adicional)
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Redactás sin inventar ni agregar contenido."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 200
    }

    for intento in range(3):
        try:
            print(f"🔁 Redacción intento {intento+1}/3")

            response = requests.post(
                URL,
                headers=headers,
                json=data,
                timeout=(5, 20)
            )

            if response.status_code == 429:
                print("⏳ Rate limit → esperando 6s...")
                time.sleep(6)
                continue

            if response.status_code != 200:
                print("❌ Error:", response.text)
                return None

            texto = response.json()["choices"][0]["message"]["content"]

            # 🔴 filtro de seguridad
            if "Después de analizar" in texto or "(Agregar" in texto:
                print("⚠️ Output inválido detectado")
                return None

            return texto

        except Exception as e:
            print("⚠️ Error:", e)
            time.sleep(4)

    return None