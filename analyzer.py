from groq_client import pedir_groq, recortar_texto


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
        "Agrupa solo noticias del MISMO hecho exacto. No agrupes mismo tema ni consecuencias. "
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
