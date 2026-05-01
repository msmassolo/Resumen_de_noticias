import html
import re

import requests


FUENTE_NOMBRE = "Finanzas Argy"
FUENTE_URL = "https://finanzasargy.com/"
DATOS_ARGY_URL = "https://www.finanzasargy.com/datos-argy"
API_DOLAR_URL = "https://x2ozxj31bl.execute-api.sa-east-1.amazonaws.com/api/dolar/v2/general"
TIMEOUT = (5, 15)


def _limpiar_texto(valor):
    texto = html.unescape(str(valor or ""))

    reemplazos = {
        "Ã³": "ó",
        "Ã­": "í",
        "Ã¡": "á",
        "Ã©": "é",
        "Ãº": "ú",
        "PaÃ­s": "País",
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    return " ".join(texto.split())


def _formatear_pesos(valor):
    valor = _limpiar_texto(valor)
    return f"$ {valor}" if valor else ""


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

    return {
        "nombre": etiqueta,
        "valor": venta,
        "detalle": f"Compra {compra}" if compra else "",
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


def _html_a_texto(html_text):
    texto = html.unescape(html_text or "")
    texto = re.sub(r"<script.*?</script>", " ", texto, flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r"<style.*?</style>", " ", texto, flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r"<[^>]+>", " ", texto)
    return _limpiar_texto(texto)


def extraer_riesgo_pais(html_text):
    texto = _html_a_texto(html_text)

    match = re.search(
        r"Riesgo\s+Pa(?:í|i)s\s+.*?(\d{1,5}(?:[.,]\d{2})?)\s*([+-]?\d+(?:[.,]\d+)?%)?",
        texto,
        re.IGNORECASE,
    )

    if not match:
        return None

    valor = _limpiar_texto(match.group(1))
    variacion = _limpiar_texto(match.group(2)) if match.group(2) else ""

    if not valor:
        return None

    return {
        "nombre": "Riesgo País",
        "valor": valor,
        "detalle": variacion,
        "actualizado": "",
    }


def obtener_riesgo_pais():
    urls = [DATOS_ARGY_URL, FUENTE_URL]

    for url in urls:
        try:
            response = requests.get(url, timeout=TIMEOUT)
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
        response = requests.get(API_DOLAR_URL, timeout=TIMEOUT)
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