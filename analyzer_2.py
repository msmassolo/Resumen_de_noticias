import json

from groq_client import pedir_groq, recortar_texto


def _extraer_eventos_y_links(texto):
    eventos = []
    links = []
    leyendo_eventos = False
    leyendo_links = False

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea == "LINKS:":
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
            eventos.extend(item.strip() for item in linea.split("|") if item.strip())

    return eventos, list(dict.fromkeys(links))


def _formatear(titulo, resumen, links):
    links_txt = "\n".join(f"- {link}" for link in links)
    return f"TITULO: {titulo}\nRESUMEN: {resumen}\nLINKS:\n{links_txt}"


def unificar_bloques(texto):
    eventos, links = _extraer_eventos_y_links(texto)

    if not eventos or not links:
        return None

    if len(eventos) == 1:
        evento = recortar_texto(eventos[0], 140)
        return _formatear(evento, evento, links)

    eventos_txt = "\n".join(f"- {recortar_texto(evento, 90)}" for evento in eventos[:4])
    prompt = (
        "Redacta una noticia unica basada solo en estos eventos. "
        'Devuelve JSON minificado: {"titulo":"max 16 palabras","resumen":"max 35 palabras"}\n'
        f"{eventos_txt}"
    )

    print(f"Groq redaccion: {len(eventos)} eventos")
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
        titulo = recortar_texto(eventos[0], 140)
    if not resumen:
        resumen = recortar_texto(" ".join(eventos[:2]), 220)

    return _formatear(titulo, resumen, links)
