import json

from bs4 import BeautifulSoup
from scrapers.utils import limpiar_titulo, normalizar_url, obtener_html


def _iter_json_items(data):
    if isinstance(data, dict):
        if data.get("@type") == "ListItem":
            yield data
        for value in data.values():
            yield from _iter_json_items(value)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_json_items(item)


def _titulares_json_ld(soup, base_url):
    titulares = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue

        for item in _iter_json_items(data):
            titulo = limpiar_titulo(str(item.get("name") or ""))
            link = normalizar_url(base_url, str(item.get("url") or ""))
            if titulo and link:
                titulares.append((titulo, link))

    return titulares


def get_clarin():

    secciones = {
        "economia": ("https://www.clarin.com/economia", 4),
        "politica": ("https://www.clarin.com/politica", 4),
        "mundo": ("https://www.clarin.com/mundo", 4)
    }

    noticias = []
    vistos = set()

    for categoria, (url, limite) in secciones.items():
        try:
            html = obtener_html(url, timeout=8)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            noticias_seccion = []

            for titulo, full_link in _titulares_json_ld(soup, url):
                if len(titulo) < 30:
                    continue

                if ".html" not in full_link:
                    continue

                if full_link in vistos:
                    continue

                vistos.add(full_link)

                noticias_seccion.append({
                    "diario": "Clarín",
                    "categoria": categoria,
                    "titulo": titulo,
                    "link": full_link
                })

            # 🔥 CLAVE: usar titulares reales
            titulares = soup.find_all(["h2", "h3"])

            for t in titulares:

                link_tag = t.find("a") or t.parent.find("a")

                if not link_tag:
                    continue

                titulo = limpiar_titulo(t.get_text(" ", strip=True))
                link = link_tag.get("href", "")

                if not titulo or not link:
                    continue

                if len(titulo) < 30:
                    continue

                # 🔴 evitar basura
                if "/autor/" in link or "/tag/" in link:
                    continue

                full_link = normalizar_url("https://www.clarin.com", link)

                # 🔴 filtro mínimo (NO agresivo)
                if not full_link.startswith("http"):
                    continue

                if ".html" not in full_link:
                    continue

                if full_link in vistos:
                    continue

                vistos.add(full_link)

                noticias_seccion.append({
                    "diario": "Clarín",
                    "categoria": categoria,
                    "titulo": titulo,
                    "link": full_link
                })

            noticias += noticias_seccion[:limite]
            print(f"Clarin {categoria}: {len(noticias_seccion[:limite])} noticias")

        except Exception as e:
            print(f"⚠️ Clarín {categoria}: {e}")

    return noticias
