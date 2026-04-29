import re
from urllib.parse import urlparse

from groq_client import pedir_groq, recortar_texto


STOPWORDS_EVENTO = {
    "actualizacion",
    "actualizo",
    "ademas",
    "argentina",
    "argentinos",
    "beneficiarios",
    "como",
    "contra",
    "cuanto",
    "desde",
    "deben",
    "debera",
    "deberan",
    "donde",
    "durante",
    "economia",
    "este",
    "esta",
    "estos",
    "estas",
    "frente",
    "gobierno",
    "hacia",
    "hasta",
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
    "mayo",
    "millones",
    "mientras",
    "noticia",
    "noticias",
    "otros",
    "para",
    "pero",
    "primera",
    "sobre",
    "tambien",
    "tendra",
    "tendran",
    "tras",
    "valor",
    "valores",
}


def _normalizar(texto):
    reemplazos = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    return (texto or "").translate(reemplazos).lower()


def _tokens_evento(item):
    link = item.get("link", "")
    slug = urlparse(link).path.replace("/", " ").replace("-", " ")
    texto = " ".join(
        [
            item.get("evento", ""),
            item.get("titulo", ""),
            slug,
        ]
    )
    tokens = re.findall(r"[a-z0-9]+", _normalizar(texto))
    return {
        token
        for token in tokens
        if len(token) >= 4 and token not in STOPWORDS_EVENTO and not token.isdigit()
    }


def _numeros_evento(item):
    texto = " ".join([item.get("evento", ""), item.get("titulo", ""), item.get("link", "")])
    return set(re.findall(r"\b\d+(?:[.,]\d+)?\b", texto))


def _son_mismo_evento(item_a, item_b):
    tokens_a = _tokens_evento(item_a)
    tokens_b = _tokens_evento(item_b)

    if not tokens_a or not tokens_b:
        return False

    comunes = tokens_a & tokens_b
    numeros_comunes = _numeros_evento(item_a) & _numeros_evento(item_b)
    union = tokens_a | tokens_b
    jaccard = len(comunes) / len(union)

    return len(comunes) >= 3 or (len(comunes) >= 2 and jaccard >= 0.18) or (numeros_comunes and len(comunes) >= 2)


def depurar_grupos(resultados, grupos):
    grupos_depurados = []

    for grupo in grupos:
        subgrupos = []

        for idx in grupo:
            if not 1 <= idx <= len(resultados):
                continue

            item = resultados[idx - 1]
            ubicado = False

            for subgrupo in subgrupos:
                if any(_son_mismo_evento(item, resultados[otro_idx - 1]) for otro_idx in subgrupo):
                    subgrupo.append(idx)
                    ubicado = True
                    break

            if not ubicado:
                subgrupos.append([idx])

        grupos_depurados.extend(subgrupos)

    return grupos_depurados


def agrupar_noticias(resultados):
    if not resultados:
        return None

    if len(resultados) == 1:
        return "[[1]]"

    items = []
    for i, r in enumerate(resultados, start=1):
        evento = recortar_texto(r.get("evento", ""), 90)
        medio = recortar_texto(r.get("diario", ""), 20)
        items.append(f"{i}|{medio}|{evento}")

    prompt = (
        "Agrupa solo noticias del MISMO hecho exacto. No agrupes mismo tema, rubro ni consecuencias. "
        "Si dos noticias hablan de economia pero de hechos distintos, deben ir separadas. "
        "Si dudas, separa. "
        "Usa cada indice una vez. Devuelve solo JSON minificado, ejemplo [[1,3],[2]].\n"
        + "\n".join(items)
    )

    max_tokens = min(220, 30 + len(resultados) * 8)
    print(f"Groq grupos: {len(resultados)} noticias, prompt {len(prompt)} chars")
    return pedir_groq(
        "Agrupas noticias por evento exacto.",
        prompt,
        max_tokens=max_tokens,
        temperature=0,
        retries=2,
    )
