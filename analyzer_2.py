import json
import re

from groq_client import pedir_groq, recortar_texto


def _normalizar(texto):
    return re.sub(r"\W+", " ", (texto or "").lower()).strip()


def _resumen_util(evento, resumen):
    resumen = (resumen or "").strip()
    if not resumen:
        return ""
    if _normalizar(resumen) == _normalizar(evento):
        return ""
    return resumen


def _extraer_items_y_links(texto):
    items = []
    links = []
    leyendo_eventos = False
    leyendo_links = False
    item_actual = None

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea == "LINKS:":
            if item_actual:
                items.append(item_actual)
                item_actual = None
            leyendo_eventos = False
            leyendo_links = True
            continue
        if linea == "EVENTOS:":
            leyendo_eventos = True
            leyendo_links = False
            continue
        if leyendo_links and linea.startswith("- http"):
            links.append(linea.replace("- ", "", 1).strip())
        elif leyendo_eventos:
            if linea.startswith("- EVENTO:"):
                if item_actual:
                    items.append(item_actual)
                item_actual = {"evento": linea.replace("- EVENTO:", "", 1).strip(), "resumen": ""}
            elif linea.startswith("RESUMEN:") and item_actual is not None:
                item_actual["resumen"] = linea.replace("RESUMEN:", "", 1).strip()
            elif "|" in linea:
                for evento in linea.split("|"):
                    evento = evento.strip()
                    if evento:
                        items.append({"evento": evento, "resumen": ""})

    if item_actual:
        items.append(item_actual)

    return items, list(dict.fromkeys(links))


def _formatear(titulo, resumen, links):
    links_txt = "\n".join(f"- {link}" for link in links)
    return f"TITULO: {titulo}\nRESUMEN: {resumen}\nLINKS:\n{links_txt}"


def unificar_bloques(texto):
    items, links = _extraer_items_y_links(texto)

    if not items or not links:
        return None

    if len(items) == 1:
        evento = recortar_texto(items[0]["evento"], 140)
        resumen = _resumen_util(evento, items[0].get("resumen")) or (
            "El texto disponible no aporta detalles adicionales verificables sobre este hecho."
        )
        return _formatear(evento, recortar_texto(resumen, 260), links)

    eventos_txt = "\n".join(
        (
            f"- Evento: {recortar_texto(item['evento'], 90)}. "
            f"Datos: {recortar_texto(_resumen_util(item['evento'], item.get('resumen')) or 'sin detalles adicionales verificables', 160)}"
        )
        for item in items[:5]
    )
    prompt = (
        "Redacta una noticia unica basada solo en los eventos y datos listados. "
        "No agregues datos externos, causas, cifras ni consecuencias que no aparezcan. "
        "El resumen debe aportar contexto verificable, no repetir el titulo. "
        'Devuelve JSON minificado: {"titulo":"max 16 palabras","resumen":"1 frase, max 45 palabras"}\n'
        f"{eventos_txt}"
    )

    print(f"Groq redaccion: {len(items)} eventos")
    respuesta = pedir_groq(
        "Redactas sintesis breves sin inventar.",
        prompt,
        max_tokens=95,
        temperature=0,
        retries=2,
    )

    try:
        data = json.loads(respuesta or "")
        titulo = str(data.get("titulo", "")).strip()
        resumen = str(data.get("resumen", "")).strip()
    except json.JSONDecodeError:
        titulo = ""
        resumen = ""
        for linea in (respuesta or "").splitlines():
            linea = linea.strip()
            if linea.startswith("TITULO:"):
                titulo = linea.replace("TITULO:", "", 1).strip()
            elif linea.startswith("RESUMEN:"):
                resumen = linea.replace("RESUMEN:", "", 1).strip()

    if not titulo:
        titulo = recortar_texto(items[0]["evento"], 140)
    if not resumen or _normalizar(resumen) == _normalizar(titulo):
        resumenes = [
            _resumen_util(item["evento"], item.get("resumen"))
            for item in items
            if _resumen_util(item["evento"], item.get("resumen"))
        ]
        resumen = recortar_texto(" ".join(resumenes[:2]), 260)
    if not resumen:
        resumen = "El texto disponible no aporta detalles adicionales verificables sobre este hecho."

    return _formatear(titulo, resumen, links)
