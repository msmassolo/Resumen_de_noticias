from bs4 import BeautifulSoup
from scrapers.utils import es_reciente, limpiar_titulo, normalizar_url, obtener_html


def get_infobae():

    secciones = {
        "economia": ("https://www.infobae.com/economia/", 4),
        "politica": ("https://www.infobae.com/politica/", 4),
        "america": ("https://www.infobae.com/america/", 4)
    }

    noticias = []
    vistos = set()

    for categoria, (url, limite) in secciones.items():
        try:
            html = obtener_html(url, timeout=10)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            noticias_seccion = []
            candidatos = 0
            descartados = 0

            for t in soup.find_all("a"):

                titulo = limpiar_titulo(t.get_text(" ", strip=True))
                link = t.get("href", "")

                if not titulo or not link:
                    continue

                candidatos += 1

                if len(titulo) < 40:
                    descartados += 1
                    continue

                if "/tag/" in link or "/autor/" in link:
                    descartados += 1
                    continue

                full_link = normalizar_url("https://www.infobae.com", link)

                # 🔴 NUEVO FILTRO
                if not full_link.startswith("http"):
                    descartados += 1
                    continue

                if len(full_link) < 60:
                    descartados += 1
                    continue

                if full_link.count("/") < 5:
                    descartados += 1
                    continue

                if full_link in vistos:
                    descartados += 1
                    continue

                if not es_reciente(str(t)):
                    descartados += 1
                    continue

                vistos.add(full_link)

                noticias_seccion.append({
                    "diario": "Infobae",
                    "categoria": categoria,
                    "titulo": titulo,
                    "link": full_link
                })

            noticias += noticias_seccion[:limite]
            print(
                f"Infobae {categoria}: {len(noticias_seccion[:limite])} noticias "
                f"({candidatos} candidatas, {descartados} descartadas)"
            )

        except Exception as e:
            print(f"⚠️ Infobae {categoria}: {e}")

    return noticias
