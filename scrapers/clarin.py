import requests
from bs4 import BeautifulSoup


def get_clarin():

    secciones = {
        "economia": ("https://www.clarin.com/economia", 1),
        "politica": ("https://www.clarin.com/politica", 1),
        "mundo": ("https://www.clarin.com/mundo", 1)
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "es-AR,es;q=0.9"
    }

    noticias = []
    vistos = set()

    for categoria, (url, limite) in secciones.items():
        try:
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            noticias_seccion = []

            # 🔥 CLAVE: usar titulares reales
            titulares = soup.find_all(["h2", "h3"])

            for t in titulares:

                link_tag = t.find("a") or t.parent.find("a")

                if not link_tag:
                    continue

                titulo = t.get_text(strip=True)
                link = link_tag.get("href", "")

                if not titulo or not link:
                    continue

                if len(titulo) < 30:
                    continue

                # 🔴 evitar basura
                if "/autor/" in link or "/tag/" in link:
                    continue

                full_link = link if link.startswith("http") else "https://www.clarin.com" + link

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

        except Exception as e:
            print(f"⚠️ Clarín {categoria}: {e}")

    return noticias