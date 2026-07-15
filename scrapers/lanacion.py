import logging

from bs4 import BeautifulSoup
from scrapers.utils import es_reciente, normalizar_url, obtener_html, titulo_mas_completo

logger = logging.getLogger(__name__)


def get_lanacion():

    secciones = {
        "economia": ("https://www.lanacion.com.ar/economia/", 4),
        "politica": ("https://www.lanacion.com.ar/politica/", 4),
        "mundo": ("https://www.lanacion.com.ar/el-mundo/", 4)
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

                titulo = titulo_mas_completo(
                    t.get_text(" ", strip=True),
                    t.get("aria-label", ""),
                    t.get("title", ""),
                )
                link = t.get("href", "")

                if not titulo or not link:
                    continue

                candidatos += 1

                if len(titulo) < 40:
                    descartados += 1
                    continue

                full_link = normalizar_url("https://www.lanacion.com.ar", link)

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
                    "diario": "La Nación",
                    "categoria": categoria,
                    "titulo": titulo,
                    "link": full_link
                })

            noticias += noticias_seccion[:limite]
            logger.info(
                "La Nacion %s: %s noticias (%s candidatas, %s descartadas)",
                categoria, len(noticias_seccion[:limite]), candidatos, descartados,
            )

        except Exception as e:
            logger.warning("⚠️ La Nación %s: %s", categoria, e)

    return noticias
