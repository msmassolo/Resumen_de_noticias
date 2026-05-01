import html
import re

import requests


FUENTE_NOMBRE = "Finanzas Argy"
FUENTE_URL = "https://finanzasargy.com/"
API_DOLAR_URL = "https://x2ozxj31bl.execute-api.sa-east-1.amazonaws.com/api/dolar/v2/general"
TIMEOUT = (5, 15)


def _limpiar_texto(valor):
    texto = html.unescape(str(valor or ""))
    texto = (
        texto.replace("Ã³", "ó")
        .replace("Ãí", "í")
        .replace("Ã­", "í")
        .replace("Ã¡", "á")
        .replace("Ã©", "é")
        .replace("Ãº", "ú")
        .replace("Ã±", "ñ")
    )
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


def extraer_riesgo_pais(html_text):
    texto = html.unescape(html_text or "")
    texto = _limpiar_texto(texto)

    patrones = [
        # Caso actual: Riesgo País 545,00 -3.88%
        r"Riesgo\s*Pa(?:ís|is)\s+(\d{2,5}(?:[.,]\d{1,2})?)\s*([+-]?\d+(?:[.,]\d+)?%)?",

        # Fallback si hay texto, tags o caracteres intermedios
        r"Riesgo\s*Pa(?:ís|is).*?(\d{2,5}(?:[.,]\d{1,2})?).{0,50}?([+-]?\d+(?:[.,]\d+)?%)?",
    ]

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)

        if match:
            valor = _limpiar_texto(match.group(1))
            variacion = _limpiar_texto(match.group(2)) if match.lastindex and match.lastindex >= 2 else ""

            if valor:
                return {
                    "nombre": "Riesgo País",
                    "valor": valor,
                    "detalle": variacion,
                    "actualizado": "",
                }

    return None


def get_datos_financieros():
    indicadores = []

    try:
        response = requests.get(API_DOLAR_URL, timeout=TIMEOUT)
        response.raise_for_status()
        indicadores.extend(extraer_dolares(response.json()))
    except Exception as e:
        print(f"No se pudieron obtener cotizaciones de dólar desde Finanzas Argy: {e}")

    try:
        response = requests.get(FUENTE_URL, timeout=TIMEOUT)
        response.raise_for_status()

        response.encoding = response.apparent_encoding

        riesgo_pais = extraer_riesgo_pais(response.text)

        if riesgo_pais:
            indicadores.append(riesgo_pais)
        else:
            print("No se pudo detectar Riesgo País en Finanzas Argy")

    except Exception as e:
        print(f"No se pudo obtener Riesgo País desde Finanzas Argy: {e}")

    return {
        "fuente": FUENTE_NOMBRE,
        "url": FUENTE_URL,
        "indicadores": indicadores,
    }