import html
import re

import requests


FUENTE_NOMBRE = "Finanzas Argy"
FUENTE_URL = "https://finanzasargy.com/"
API_DOLAR_URL = "https://x2ozxj31bl.execute-api.sa-east-1.amazonaws.com/api/dolar/v2/general"
TIMEOUT = (5, 15)


def _limpiar_texto(valor):
    texto = html.unescape(str(valor or ""))
    texto = texto.replace("Ã³", "ó").replace("Ã­", "í").replace("Ã¡", "á").replace("Ã©", "é").replace("Ãº", "ú")
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


def _extraer_riesgo_pais_estructura(texto):
    match = re.search(
        r'Riesgo Pa(?:ís|Ã­s).*?valor"\s*:\s*\[0,\s*"([^"]+)"\].*?variacion"\s*:\s*\[0,\s*"([^"]+)"\]',
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None

    return _limpiar_texto(match.group(1)), _limpiar_texto(match.group(2))


def _extraer_riesgo_pais_texto(texto):
    texto = texto.replace("Ã³", "ó").replace("Ã­", "í").replace("Ã¡", "á").replace("Ã©", "é").replace("Ãº", "ú")

    patterns = [
        r'(\d[\d\.,]*)\s*([+-]?\d[\d\.,]*%)\s*RIESGO\s*PA[IÍ]S',
        r'RIESGO\s*PA[IÍ]S.*?(\d[\d\.,]*)\s*([+-]?\d[\d\.,]*%)',
        r'(\d[\d\.,]*)\s*RIESGO\s*PA[IÍ]S',
    ]

    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE | re.DOTALL)
        if not match:
            continue

        if len(match.groups()) >= 2 and match.group(2):
            return _limpiar_texto(match.group(1)), _limpiar_texto(match.group(2))

        if len(match.groups()) >= 1:
            return _limpiar_texto(match.group(1)), ""

    return None


def extraer_riesgo_pais(html_text):
    texto = html.unescape(html_text or "")

    resultado = _extraer_riesgo_pais_estructura(texto)
    if resultado:
        valor, variacion = resultado
    else:
        resultado = _extraer_riesgo_pais_texto(texto)
        if not resultado:
            return None
        valor, variacion = resultado

    if not valor:
        return None

    return {
        "nombre": "Riesgo País",
        "valor": valor,
        "detalle": variacion,
        "actualizado": "",
    }


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
        riesgo_pais = extraer_riesgo_pais(response.text)
        if riesgo_pais:
            indicadores.append(riesgo_pais)
    except Exception as e:
        print(f"No se pudo obtener Riesgo País desde Finanzas Argy: {e}")

    return {
        "fuente": FUENTE_NOMBRE,
        "url": FUENTE_URL,
        "indicadores": indicadores,
    }