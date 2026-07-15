import json
import logging
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_CONTENIDO_CHARS = 2600
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "igshid"}


def normalizar_url(base_url, link):
    if not link:
        return ""

    url = urljoin(base_url, link.strip())
    partes = urlsplit(url)

    if partes.scheme not in {"http", "https"}:
        return ""

    query = [
        (clave, valor)
        for clave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if clave not in TRACKING_QUERY_KEYS and not clave.startswith(TRACKING_QUERY_PREFIXES)
    ]

    return urlunsplit(
        (
            partes.scheme,
            partes.netloc.lower(),
            partes.path,
            urlencode(query, doseq=True),
            "",
        )
    )


def limpiar_titulo(texto):
    texto = " ".join((texto or "").split())
    texto = re.sub(r"([a-záéíóúñ])\.([A-ZÁÉÍÓÚÑ])", r"\1. \2", texto)
    texto = re.sub(r"([a-záéíóúñ])Por([A-ZÁÉÍÓÚÑ])", r"\1 Por \2", texto)
    texto = re.sub(r"\bPor([A-ZÁÉÍÓÚÑ])", r"Por \1", texto)
    texto = re.sub(r"([a-záéíóúñ])EN VIVO", r"\1 EN VIVO", texto)
    return texto.strip()


def recortar_en_limite_natural(texto, max_chars):
    texto = " ".join((texto or "").split())
    if len(texto) <= max_chars:
        return texto

    recorte = texto[:max_chars].rsplit(" ", 1)[0].strip()
    ultimo_cierre = max(recorte.rfind("."), recorte.rfind("!"), recorte.rfind("?"))
    if ultimo_cierre >= int(max_chars * 0.55):
        return recorte[: ultimo_cierre + 1].strip()

    return recorte


def titulo_mas_completo(*candidatos):
    titulos = [limpiar_titulo(candidato) for candidato in candidatos if limpiar_titulo(candidato)]
    if not titulos:
        return ""

    return max(titulos, key=lambda titulo: (len(titulo), titulo.count(" ")))


def obtener_html(url, timeout=10):
    try:
        response = SESSION.get(url, timeout=timeout)

        if response.status_code != 200:
            logger.warning("Pagina respondio %s: %s", response.status_code, url)
            return ""

        # Evita mojibake cuando el servidor no declara charset (requests asume
        # ISO-8859-1 por defecto para text/*).
        if not response.encoding or "charset" not in response.headers.get("Content-Type", "").lower():
            response.encoding = response.apparent_encoding or response.encoding

        return response.text

    except requests.exceptions.Timeout:
        logger.warning("Timeout al cargar: %s", url)
        return ""

    except requests.exceptions.RequestException as e:
        logger.warning("Error en request %s: %s", url, e)
        return ""


def _iter_json_ld(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from _iter_json_ld(value)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_json_ld(item)


def _texto_desde_json_ld(soup):
    textos = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = script.string or script.get_text()
            parsed = json.loads(data)
        except Exception:
            continue

        for item in _iter_json_ld(parsed):
            tipo = item.get("@type")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if not any(str(t).lower() in {"newsarticle", "article"} for t in tipos):
                continue

            for key in ("articleBody", "description"):
                valor = item.get(key)
                if isinstance(valor, str):
                    texto = " ".join(valor.split())
                    if len(texto) > 180:
                        textos.append(texto)

    return "\n".join(dict.fromkeys(textos))


def _parrafos_candidatos(soup):
    contenedor = soup.find("article") or soup.find("main") or soup
    parrafos = contenedor.find_all("p")

    if len(parrafos) < 3 and contenedor is not soup:
        parrafos = soup.find_all("p")

    return parrafos


def obtener_contenido_detalle(link):
    try:
        html = obtener_html(link, timeout=8)
        if not html:
            return "", "sin_html"

        soup = BeautifulSoup(html, "html.parser")
        texto_json_ld = _texto_desde_json_ld(soup)
        if texto_json_ld:
            return recortar_en_limite_natural(texto_json_ld, MAX_CONTENIDO_CHARS), "json_ld"

        textos = []
        vistos = set()

        for p in _parrafos_candidatos(soup):
            contenido = " ".join(p.get_text(" ", strip=True).split())
            if len(contenido) > 50:
                clave = contenido.lower()
                if clave not in vistos:
                    textos.append(contenido)
                    vistos.add(clave)

        texto = "\n".join(textos)

        if len(texto) < 180:
            logger.warning("Contenido insuficiente: %s", link)
            return "", "contenido_insuficiente"

        return recortar_en_limite_natural(texto, MAX_CONTENIDO_CHARS), "parrafos"

    except Exception as e:
        logger.warning("Error parseando contenido: %s", e)
        return "", "error_parseo"


def es_reciente(texto_html):
    texto = texto_html.lower()

    # Señales explícitas de contenido viejo: descartar.
    if re.search(r"hace \d+ (semana|mes|año|anio)", texto):
        return False
    if re.search(r"(semana|mes|año|anio) pasad[oa]", texto):
        return False

    match = re.search(r"hace (\d+) minuto", texto)
    if match:
        return True

    match = re.search(r"hace (\d+) hora", texto)
    if match:
        horas = int(match.group(1))
        return horas <= 36

    match = re.search(r"hace (\d+) d[ií]a", texto)
    if match:
        dias = int(match.group(1))
        return dias <= 1

    # Sin señal temporal en el markup del enlace: se incluye (default permisivo
    # para no vaciar el feed; la recencia real la garantiza la sección del diario).
    return True
