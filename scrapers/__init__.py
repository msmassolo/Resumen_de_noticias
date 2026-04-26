from .infobae import get_infobae
from .lanacion import get_lanacion
from .clarin import get_clarin

def obtener_todo():
    noticias = []

    try:
        noticias += get_infobae()
    except Exception as e:
        print(f"⚠️ Error Infobae: {e}")

    try:
        noticias += get_lanacion()
    except Exception as e:
        print(f"⚠️ Error La Nación: {e}")

    try:
        noticias += get_clarin()
    except Exception as e:
        print(f"⚠️ Error Clarín: {e}")

    return noticias
