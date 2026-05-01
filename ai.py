import json
import re

from groq_client import pedir_groq, recortar_texto


MAX_CONTENIDO_CHARS = 1100


def _normalizar(texto):
    return re.sub(r"\W+", " ", (texto or "").lower()).strip()


def _resumen_fallback(titulo, contenido):
    titulo_norm = _normalizar(titulo)
    oraciones = re.split(r"(?<=[.!?])\s+", " ".join((contenido or "").split()))
    candidatas = []

    for oracion in oraciones:
        oracion = oracion.strip()
        if len(oracion) < 80:
            continue
        if _normalizar(oracion) == titulo_norm:
            continue
        candidatas.append(oracion)
        if len(candidatas) == 2:
            break

    if candidatas:
        return recortar_texto(" ".join(candidatas), 260)

    return "El texto disponible no aporta detalles adicionales verificables sobre este hecho."


def _parsear_respuesta(texto, titulo, contenido):
    if not texto:
        return {"evento": titulo[:120], "resumen": _resumen_fallback(titulo, contenido), "enfoque": ""}

    try:
        data = json.loads(texto)
        evento = str(data.get("evento") or "").strip()
        resumen = str(data.get("resumen") or "").strip()
        enfoque = str(data.get("enfoque") or "").strip()
    except json.JSONDecodeError:
        evento = ""
        resumen = ""
        enfoque = ""
        for linea in texto.splitlines():
            linea = linea.strip()
            if linea.startswith("EVENTO:"):
                evento = linea.replace("EVENTO:", "", 1).strip()
            elif linea.startswith("RESUMEN:"):
                resumen = linea.replace("RESUMEN:", "", 1).strip()
            elif linea.startswith("ENFOQUE:"):
                enfoque = linea.replace("ENFOQUE:", "", 1).strip()

    evento = evento or titulo[:120]
    if not resumen or _normalizar(resumen) in {_normalizar(evento), _normalizar(titulo)}:
        resumen = _resumen_fallback(titulo, contenido)

    if enfoque and _normalizar(enfoque) in {_normalizar(evento), _normalizar(titulo), _normalizar(resumen)}:
        enfoque = ""

    return {"evento": evento, "resumen": resumen, "enfoque": enfoque}


def procesar_noticia(titulo, contenido):
    contenido = recortar_texto(contenido, MAX_CONTENIDO_CHARS)
    prompt = (
        "Extrae el hecho central, un resumen informativo y el enfoque editorial verificable. No inventes nombres, cifras, causas ni consecuencias. "
        "El resumen debe explicar actor, accion, contexto o consecuencia solo si aparecen en el texto. "
        "El enfoque debe indicar si el medio atribuye responsabilidad, culpa, causa, critica, defensa o contraste politico; si no aparece, dejalo vacio. "
        "No copies el titulo como resumen. Si no hay detalles adicionales verificables, dilo explicitamente. "
        'Devuelve JSON minificado: {"evento":"max 14 palabras","resumen":"1 frase, max 34 palabras","enfoque":"max 24 palabras o vacio"}\n'
        f"TITULO: {titulo}\nTEXTO: {contenido}"
    )

    print(f"Groq evento: {titulo[:60]}...")
    texto = pedir_groq(
        "Extraes hechos concretos de noticias.",
        prompt,
        max_tokens=125,
        temperature=0,
        retries=1,
    )
    return _parsear_respuesta(texto, titulo, contenido)
