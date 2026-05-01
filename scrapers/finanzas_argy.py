import html
import re

import requests
from bs4 import BeautifulSoup


FUENTE_NOMBRE = "Finanzas Argy"
FUENTE_URL = "https://finanzasargy.com/"
DATOS_ARGY_URL = "https://www.finanzasargy.com/datos-argy"
API_DOLAR_URL = "https://x2ozxj31bl.execute-api.sa-east-1.amazonaws.com/api/dolar/v2/general"

TIMEOUT = (5, 15)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def _limpiar_texto(valor):
    texto = html.unescape(str(valor or ""))

    reemplazos = {
        "Ã³": "ó",
        "Ã­": "í",
        "Ã¡": "á",
        "Ã©": "é",
        "Ãº": "ú",
        "Ã±": "ñ",
        "PaÃ­s": "País",
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    return " ".join(texto.split())


def _formatear_pesos(valor):
    valor = _limpiar_texto(valor)
    if not valor:
        return ""
    return f"$ {valor}"


def _buscar_panel(panel, titulo_objetivo):
    objetivo = _limpiar_texto(titulo_objetivo).lower()

    for item in panel or []:
        titulo = _limpiar_texto(item.get("titulo")).lower()
        if titulo == objetivo:
            return item

    return None


def _indicador_dolar(panel, titulo, etiqueta):
    item = _buscar_panel(panel, titulo)
    if not item:
        return None

    venta = _formatear_pesos(item.get("venta"))
    compra = _formatear_pesos(item.get("compra"))
    fecha = _limpiar_texto(item.get("fecha") or item.get("lastUpdate"))

    if not venta:
        return None

    detalle = f"Compra {compra}" if compra else ""

    return {
        "nombre": etiqueta,
        "valor": venta,
        "detalle": detalle,
        "actualizado": fecha,
    }


def extraer_dolares(payload):
    panel = (payload or {}).get("data", {}).get("panel", [])
    indicadores = []

    for titulo, etiqueta in (
        ("Dólar Blue", "Dólar Blue"),
        ("Dólar Oficial", "Dólar Oficial"),
        ("Dólar MEP", "Dólar MEP"),
    ):
        indicador = _indicador_dolar(panel, titulo, etiqueta)
        if indicador:
            indicadores.append(indicador)

    return indicadores


def _normalizar_html_a_lineas(html_text):
    soup = BeautifulSoup(html_text or "", "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    texto = soup.get_text("\n")
    lineas = []

    for linea in texto.splitlines():
        linea = _limpiar_texto(linea)
        if linea:
            lineas.append(linea)

    return lineas


def extraer_riesgo_pais(html_text):
    lineas = _normalizar_html_a_lineas(html_text)

    for i, linea in enumerate(lineas):
        if re.search(r"Riesgo\s+Pa(?:í|i)s", linea, re.IGNORECASE):
            bloque = " ".join(lineas[i:i + 8])

            match = re.search(
                r"(\d{3,5}(?:[.,]\d{2})?)\s*([+-]?\d+(?:[.,]\d+)?%)?",
                bloque
            )

            if not match:
                continue

            valor = _limpiar_texto(match.group(1))
            variacion = _limpiar_texto(match.group(2)) if match.group(2) else ""

            return {
                "nombre": "Riesgo País",
                "valor": valor,
                "detalle": variacion,
                "actualizado": "",
            }

    return None


def obtener_riesgo_pais():
    urls = [DATOS_ARGY_URL, FUENTE_URL]

    for url in urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()

            riesgo_pais = extraer_riesgo_pais(response.text)

            if riesgo_pais:
                return riesgo_pais

        except Exception as e:
            print(f"No se pudo obtener Riesgo País desde {url}: {e}")

    print("No se pudo encontrar el dato de Riesgo País en Finanzas Argy")
    return None


def get_datos_financieros():
    indicadores = []

    try:
        response = requests.get(API_DOLAR_URL, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        indicadores.extend(extraer_dolares(response.json()))
    except Exception as e:
        print(f"No se pudieron obtener cotizaciones de dólar desde Finanzas Argy: {e}")

    riesgo_pais = obtener_riesgo_pais()
    if riesgo_pais:
        indicadores.append(riesgo_pais)

    return {
        "fuente": FUENTE_NOMBRE,
        "url": FUENTE_URL,
        "indicadores": indicadores,
    }