import html
import json
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


def _normalizar_numero(valor):
    valor = _limpiar_texto(valor)

    # elimina caracteres raros
    valor = re.sub(r"[^\d,.\-+%]", "", valor)

    return valor.strip()


def extraer_riesgo_pais(html_text):
    """
    Estrategia robusta:
    1. Busca JSON embebido
    2. Busca bloques cercanos a 'Riesgo País'
    3. Busca patrones flexibles
    """

    texto = html.unescape(html_text or "")

    # ------------------------------------------------------------------
    # OPCION 1: Buscar estructura tipo JSON
    # ------------------------------------------------------------------

    patrones_json = [
        r'Riesgo\s*Pa(?:ís|is).*?valor"\s*:\s*\[0,\s*"([^"]+)"\].*?variacion"\s*:\s*\[0,\s*"([^"]+)"\]',
        r'Riesgo\s*Pa(?:ís|is).*?"valor"\s*:\s*"([^"]+)".*?"variacion"\s*:\s*"([^"]+)"',
    ]

    for patron in patrones_json:
        match = re.search(
            patron,
            texto,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            valor = _normalizar_numero(match.group(1))
            variacion = _normalizar_numero(match.group(2))

            if valor:
                return {
                    "nombre": "Riesgo País",
                    "valor": valor,
                    "detalle": variacion,
                    "actualizado": "",
                }

    # ------------------------------------------------------------------
    # OPCION 2: Buscar cerca del texto "Riesgo País"
    # ------------------------------------------------------------------

    match_bloque = re.search(
        r'Riesgo\s*Pa(?:ís|is)(.{0,600})',
        texto,
        re.IGNORECASE | re.DOTALL,
    )

    if match_bloque:
        bloque = match_bloque.group(1)

        # busca numeros tipo 741 / 1.245
        numeros = re.findall(r'\b\d{2,5}(?:[.,]\d{1,2})?\b', bloque)

        # busca variacion tipo +1,2% / -0,8%
        variaciones = re.findall(
            r'[+-]?\d+(?:[.,]\d+)?%',
            bloque,
        )

        valor = numeros[0] if numeros else ""
        variacion = variaciones[0] if variaciones else ""

        if valor:
            return {
                "nombre": "Riesgo País",
                "valor": _normalizar_numero(valor),
                "detalle": _normalizar_numero(variacion),
                "actualizado": "",
            }

    # ------------------------------------------------------------------
    # OPCION 3: Buscar cualquier referencia global
    # ------------------------------------------------------------------

    patrones_generales = [
        r'Riesgo\s*Pa(?:ís|is).*?(\d{2,5})',
        r'EMBI.*?Argentina.*?(\d{2,5})',
    ]

    for patron in patrones_generales:
        match = re.search(
            patron,
            texto,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            valor = _normalizar_numero(match.group(1))

            if valor:
                return {
                    "nombre": "Riesgo País",
                    "valor": valor,
                    "detalle": "",
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

        # MUY IMPORTANTE:
        # fuerza encoding correcto
        response.encoding = response.apparent_encoding

        riesgo_pais = extraer_riesgo_pais(response.text)

        if riesgo_pais:
            indicadores.append(riesgo_pais)
        else:
            print("No se pudo detectar Riesgo País en el HTML")

    except Exception as e:
        print(f"No se pudo obtener Riesgo País desde Finanzas Argy: {e}")

    return {
        "fuente": FUENTE_NOMBRE,
        "url": FUENTE_URL,
        "indicadores": indicadores,
    }