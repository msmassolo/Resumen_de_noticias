from .infobae import get_infobae
from .lanacion import get_lanacion
from .clarin import get_clarin
from .utils import normalizar_url
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)


def _normalizar_titulo(titulo):
    texto = unicodedata.normalize("NFKD", titulo or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-zA-Z0-9]+", " ", texto).lower()
    return " ".join(texto.split())


def _deduplicar(noticias):
    resultado = []
    links_vistos = set()
    titulos_por_medio = set()

    for noticia in noticias:
        link = normalizar_url(noticia.get("link", ""), noticia.get("link", ""))
        titulo_key = (noticia.get("diario", ""), _normalizar_titulo(noticia.get("titulo", "")))

        if not link or link in links_vistos or titulo_key in titulos_por_medio:
            continue

        noticia["link"] = link
        resultado.append(noticia)
        links_vistos.add(link)
        titulos_por_medio.add(titulo_key)

    return resultado


def obtener_todo():
    noticias = []

    try:
        noticias += get_infobae()
    except Exception as e:
        logger.warning("⚠️ Error Infobae: %s", e)

    try:
        noticias += get_lanacion()
    except Exception as e:
        logger.warning("⚠️ Error La Nación: %s", e)

    try:
        noticias += get_clarin()
    except Exception as e:
        logger.warning("⚠️ Error Clarín: %s", e)

    noticias = _deduplicar(noticias)
    logger.info("Total tras deduplicar: %s noticias", len(noticias))
    return noticias
