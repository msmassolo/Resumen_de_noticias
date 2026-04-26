import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re


def obtener_contenido(link):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "es-AR,es;q=0.9"
    }

    try:
        response = requests.get(link, headers=headers, timeout=5)

        if response.status_code != 200:
            print("⚠️ Página respondió mal")
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        parrafos = soup.find_all("p")

        texto = ""

        for p in parrafos:
            contenido = p.get_text(strip=True)

            if len(contenido) > 50:
                texto += contenido + "\n"

        return texto[:2000]

    except requests.exceptions.Timeout:
        print("⚠️ Timeout al cargar noticia")
        return ""

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error en request: {e}")
        return ""

    except Exception as e:
        print(f"⚠️ Error parseando contenido: {e}")
        return ""


# 🔴 NUEVO: filtro de noticias recientes (últimas 36 hs)
def es_reciente(texto_html):
    texto = texto_html.lower()

    match = re.search(r"hace (\d+) hora", texto)
    if match:
        horas = int(match.group(1))
        return horas <= 36

    match = re.search(r"hace (\d+) minuto", texto)
    if match:
        return True

    # fallback → no filtra si no encuentra info temporal
    return True