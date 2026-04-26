import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno (.env en local / Secrets en GitHub)
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("❌ GROQ_API_KEY no está cargada")

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"


def procesar_noticia(titulo, contenido):

    prompt = f"""
Sos un sistema que extrae el HECHO PRINCIPAL de una noticia.

Título:
{titulo}

Contenido:
{contenido}

Tu tarea es identificar el EVENTO CENTRAL.

⚠️ DEFINICIÓN DE EVENTO:

El evento debe incluir SIEMPRE:
- QUIÉN (actor principal: persona, país, institución)
- QUÉ PASÓ (acción concreta)
- CONTEXTO mínimo

👉 Debe ser un hecho puntual, NO un tema general.

---

⚠️ EJEMPLOS CORRECTOS:

✔ "Luis Caputo anticipa mayor inflación en febrero"
✔ "Israel lanza ataque contra Irán en conflicto regional"
✔ "Industria pesquera advierte impacto por aumento del gasoil"

---

❌ EJEMPLOS INCORRECTOS:

❌ "situación económica en Argentina"
❌ "problemas de inflación"
❌ "crisis política"

---

⚠️ REGLAS ESTRICTAS:

- NO mezclar noticias
- NO generalizar
- NO interpretar
- NO inventar
- Si no es claro → usar SOLO el título

---

Devolver EXACTAMENTE:

EVENTO: (máximo 15 palabras)
RESUMEN: (máximo 2 líneas)

NO agregar nada más.
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Extraés eventos concretos sin inventar."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 300
    }

    try:
        print(f"📡 Groq: {titulo[:60]}...")

        response = requests.post(
            URL,
            headers=headers,
            json=data,
            timeout=(3, 7)
        )

        if response.status_code != 200:
            return {"evento": titulo[:120], "resumen": titulo[:150]}

        result = response.json()
        texto = result["choices"][0]["message"]["content"]

        evento = ""
        resumen = ""

        for linea in texto.split("\n"):
            linea = linea.strip()

            if linea.startswith("EVENTO:"):
                evento = linea.replace("EVENTO:", "").strip()

            elif linea.startswith("RESUMEN:"):
                resumen = linea.replace("RESUMEN:", "").strip()

        # 🔥 FALLBACK CRÍTICO
        if not evento:
            evento = titulo[:120]

        if not resumen:
            resumen = titulo[:150]

        return {
            "evento": evento,
            "resumen": resumen
        }

    except Exception as e:
        print(f"⚠️ Error IA: {e}")
        return {
            "evento": titulo[:120],
            "resumen": titulo[:150]
        }