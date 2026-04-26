import requests
from bs4 import BeautifulSoup
from scrapers.utils import es_reciente


def get_lanacion():

    secciones = {
        "economia": ("https://www.lanacion.com.ar/economia/", 4),
        "politica": ("https://www.lanacion.com.ar/politica/", 4),
        "mundo": ("https://www.lanacion.com.ar/el-mundo/", 4)
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    noticias = []
    vistos = set()

    for categoria, (url, limite) in secciones.items():
        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            noticias_seccion = []

            for t in soup.find_all("a"):

                titulo = t.get_text(strip=True)
                link = t.get("href", "")

                if not titulo or not link:
                    continue

                if len(titulo) < 40:
                    continue

                full_link = link if link.startswith("http") else "https://www.lanacion.com.ar" + link

                # 🔴 NUEVO FILTRO
                if not full_link.startswith("http"):
                    continue

                if len(full_link) < 60:
                    continue

                if full_link.count("/") < 5:
                    continue

                if full_link in vistos:
                    continue

                if not es_reciente(str(t)):
                    continue

                vistos.add(full_link)

                noticias_seccion.append({
                    "diario": "La Nación",
                    "categoria": categoria,
                    "titulo": titulo,
                    "link": full_link
                })

            noticias += noticias_seccion[:limite]

        except Exception as e:
            print(f"⚠️ La Nación {categoria}: {e}")

    return noticias