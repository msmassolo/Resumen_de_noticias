import json

from groq_client import pedir_groq, recortar_texto


MAX_CONTENIDO_CHARS = 1100


def _parsear_respuesta(texto, titulo):
    if not texto:
        return {"evento": titulo[:120], "resumen": titulo[:150]}

    try:
        data = json.loads(texto)
        evento = str(data.get("evento", "")).strip()
        resumen = str(data.get("resumen", "")).strip()
    except json.JSONDecodeError:
        evento = ""
        resumen = ""
        for linea in texto.splitlines():
            linea = linea.strip()
            if linea.startswith("EVENTO:"):
                evento = linea.replace("EVENTO:", "", 1).strip()
            elif linea.startswith("RESUMEN:"):
                resumen = linea.replace("RESUMEN:", "", 1).strip()

    return {
        "evento": evento or titulo[:120],
        "resumen": resumen or titulo[:150],
    }


def procesar_noticia(titulo, contenido):
    contenido = recortar_texto(contenido, MAX_CONTENIDO_CHARS)
    prompt = (
        "Extrae el hecho central. No inventes. Si el texto no alcanza, usa el titulo. "
        'Devuelve JSON minificado: {"evento":"max 14 palabras","resumen":"max 24 palabras"}\n'
        f"TITULO: {titulo}\nTEXTO: {contenido}"
    )

    print(f"Groq evento: {titulo[:60]}...")
    texto = pedir_groq(
        "Extraes hechos concretos de noticias.",
        prompt,
        max_tokens=90,
        temperature=0,
        retries=1,
    )
    return _parsear_respuesta(texto, titulo)
