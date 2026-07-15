from logging_config import configurar_logging

configurar_logging()

from scrapers import obtener_todo
from scrapers.finanzas_argy import get_datos_financieros
from scrapers.utils import limpiar_titulo, obtener_contenido_detalle
from ai import procesar_noticia
from analyzer import agrupar_noticias, depurar_grupos
from analyzer_2 import unificar_bloques

from web_generator import generar_web
from groq_client import MODEL

import argparse
import json
import logging
import os
import sys
import time
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CACHE_IA_PATH = ".cache_ai.json"
CACHE_IA_TTL_DIAS = int(os.getenv("CACHE_IA_TTL_DIAS", "3"))
CACHE_IA_VERSION = "evento-resumen-enfoque-contenido-v4"
ARTIFACTS_DIR = Path("data")
GITHUB_REPO_URL = "https://github.com/msmassolo/Resumen_de_noticias.git"


def configurar_salida_utf8():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configurar_salida_utf8()


def cargar_cache_ia():
    try:
        with open(CACHE_IA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning("⚠️ No se pudo leer cache IA: %s", e)
        return {}


def guardar_cache_ia(cache):
    try:
        with open(CACHE_IA_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("⚠️ No se pudo guardar cache IA: %s", e)


# 🔥 NUEVO: función para subir a GitHub
def _ahora_utc():
    return datetime.now(timezone.utc)


def _parsear_fecha_cache(valor):
    if not valor:
        return None

    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def leer_cache_ia(cache, link):
    entrada = cache.get(link)

    if not isinstance(entrada, dict):
        return None

    if entrada.get("version") != CACHE_IA_VERSION:
        return None

    if entrada.get("model") != MODEL:
        return None

    creado = _parsear_fecha_cache(entrada.get("creado"))
    if not creado:
        return None

    if _ahora_utc() - creado > timedelta(days=CACHE_IA_TTL_DIAS):
        return None

    data = entrada.get("data")
    if isinstance(data, dict) and data.get("evento") and data.get("resumen"):
        return data

    return None


def escribir_cache_ia(cache, link, data):
    cache[link] = {
        "version": CACHE_IA_VERSION,
        "model": MODEL,
        "creado": _ahora_utc().isoformat(),
        "data": data,
    }


def guardar_json_intermedio(nombre, data):
    try:
        ARTIFACTS_DIR.mkdir(exist_ok=True)
        path = ARTIFACTS_DIR / nombre
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("No se pudo guardar %s: %s", nombre, e)


def guardar_texto_intermedio(nombre, texto):
    try:
        ARTIFACTS_DIR.mkdir(exist_ok=True)
        path = ARTIFACTS_DIR / nombre
        with open(path, "w", encoding="utf-8") as f:
            f.write(texto)
    except Exception as e:
        logger.warning("No se pudo guardar %s: %s", nombre, e)


def subir_index_github():
    if os.getenv("GITHUB_ACTIONS") == "true":
        logger.info("GitHub Actions se encarga del commit/push final.")
        return

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN no esta definido en .env")

    repo_url = os.getenv("GITHUB_REPO_URL", GITHUB_REPO_URL)
    if not repo_url.startswith("https://github.com/"):
        raise ValueError("GITHUB_REPO_URL debe ser una URL HTTPS de GitHub")

    logger.info("🚀 Subiendo index.html a GitHub...")
    askpass_path = None

    try:
        with tempfile.NamedTemporaryFile("w", suffix=".cmd", delete=False, encoding="utf-8") as f:
            askpass_path = f.name
            f.write("@echo off\n")
            f.write('echo %~1 | findstr /I "Username" >nul\n')
            f.write("if not errorlevel 1 (\n")
            f.write("  echo x-access-token\n")
            f.write(") else (\n")
            f.write('  powershell -NoProfile -Command "[Console]::Out.Write($env:GITHUB_TOKEN)"\n')
            f.write(")\n")

        env = os.environ.copy()
        env["GITHUB_TOKEN"] = token
        env["GIT_ASKPASS"] = askpass_path
        env["GIT_TERMINAL_PROMPT"] = "0"

        subprocess.run(["git", "add", "index.html"], check=True)
        subprocess.run(["git", "commit", "-m", "update automatico"], check=False)
        subprocess.run(
            [
                "git",
                "-c",
                "credential.helper=",
                "push",
                repo_url,
                "HEAD:main",
            ],
            check=True,
            env=env,
        )

        logger.info("✅ Web actualizada en GitHub Pages")

    except subprocess.CalledProcessError as e:
        logger.error("⚠️ Error subiendo a GitHub. Comando git fallo con codigo %s.", e.returncode)

    except Exception as e:
        logger.error("⚠️ Error subiendo a GitHub: %s", e)

    finally:
        if askpass_path:
            try:
                os.unlink(askpass_path)
            except OSError:
                pass


def parsear_grupos(texto):
    if not texto:
        return []

    try:
        data = json.loads(texto)
        grupos = []
        usados = set()

        for grupo in data:
            grupo_limpio = []
            for idx in grupo:
                idx = int(idx)
                if idx > 0 and idx not in usados:
                    grupo_limpio.append(idx)
                    usados.add(idx)
            if grupo_limpio:
                grupos.append(grupo_limpio)

        if grupos:
            return grupos
    except Exception:
        pass

    grupos = []
    grupo_actual = []
    usados = set()

    for linea in texto.split("\n"):
        linea = linea.strip()

        if linea.startswith("GRUPO"):
            if grupo_actual:
                grupos.append(grupo_actual)
                grupo_actual = []

        elif linea.startswith("-"):
            try:
                idx = int(linea.replace("-", "").strip())
                if idx > 0 and idx not in usados:
                    grupo_actual.append(idx)
                    usados.add(idx)
            except:
                pass

    if grupo_actual:
        grupos.append(grupo_actual)

    return grupos


def normalizar_categoria(categoria):
    cat = limpiar_titulo(categoria or "general").lower()

    if cat in {"economia", "economía"} or "eco" in cat:
        return "economia"
    if cat in {"politica", "política"} or "pol" in cat:
        return "politica"
    if cat in {"america", "mundo", "el mundo", "internacional", "internacionales"}:
        return "internacional"
    return "general"


def extraer_noticia_unificada(categoria, texto):
    titulo = ""
    resumen = ""
    links = []
    capturando_resumen = False

    for linea in (texto or "").splitlines():
        linea = linea.strip()

        if not linea:
            continue

        if linea.startswith("TITULO:"):
            titulo = linea.replace("TITULO:", "", 1).strip()
            capturando_resumen = False
        elif linea.startswith("RESUMEN:"):
            resumen = linea.replace("RESUMEN:", "", 1).strip()
            capturando_resumen = True
        elif linea.startswith("LINKS:"):
            capturando_resumen = False
        elif linea.startswith("- http"):
            links.append(linea.replace("- ", "", 1).strip())
            capturando_resumen = False
        elif capturando_resumen:
            resumen = f"{resumen}\n{linea}".strip()

    links = list(dict.fromkeys(link for link in links if link.startswith(("http://", "https://"))))

    if not titulo and not resumen and not links:
        return None

    return {
        "categoria": categoria.upper(),
        "titulo": titulo,
        "resumen": resumen,
        "links": links,
    }


def _texto_equivalente(a, b):
    return limpiar_titulo(a).lower() == limpiar_titulo(b).lower()


def _normalizar_para_comparar(texto):
    return limpiar_titulo(texto).lower()


def _recortar_evento_pegado_a_titulo(evento, titulo):
    evento_normalizado = _normalizar_para_comparar(evento)
    titulo_normalizado = _normalizar_para_comparar(titulo)

    if titulo_normalizado and evento_normalizado.startswith(f"{titulo_normalizado} "):
        return limpiar_titulo(titulo)

    return evento


def normalizar_resultado_ia(data, titulo):
    if not isinstance(data, dict):
        data = {}

    evento = str(data.get("evento") or "").strip()
    resumen = str(data.get("resumen") or "").strip()
    enfoque = str(data.get("enfoque") or "").strip()

    evento = limpiar_titulo(evento or titulo[:120])
    evento = _recortar_evento_pegado_a_titulo(evento, titulo)
    resumen = limpiar_titulo(resumen or "")
    enfoque = limpiar_titulo(enfoque or "")

    if not resumen or _texto_equivalente(resumen, evento) or _texto_equivalente(resumen, titulo):
        resumen = "El texto disponible no aporta detalles adicionales verificables sobre este hecho."

    if enfoque and (
        _texto_equivalente(enfoque, evento)
        or _texto_equivalente(enfoque, resumen)
        or _texto_equivalente(enfoque, titulo)
    ):
        enfoque = ""

    return {"evento": evento, "resumen": resumen, "enfoque": enfoque}


def ejecutar_proyecto(publicar=False):
    logger.info("--- INICIANDO RECOLECCIÓN DE NOTICIAS ---")

    noticias = obtener_todo()
    guardar_json_intermedio("raw_news.json", noticias)
    logger.info("📰 Total noticias: %s", len(noticias))

    resultados = []
    cache_ia = cargar_cache_ia()
    cache_modificada = False
    cache_hits = 0
    cache_misses = 0
    sin_contenido = 0
    fallos_contenido = {}

    # 🔴 ETAPA 1: IA
    for i, n in enumerate(noticias, start=1):
        logger.info("🔎 [%s/%s] %s", i, len(noticias), n["diario"])
        logger.info("📰 %s...", n["titulo"][:80])

        cache_key = n["link"]
        data = leer_cache_ia(cache_ia, cache_key)
        if data:
            cache_hits += 1
            logger.info("✅ Cache IA")
        else:
            cache_misses += 1
            contenido, motivo_contenido = obtener_contenido_detalle(n["link"])

            if not contenido:
                sin_contenido += 1
                fallos_contenido[motivo_contenido] = fallos_contenido.get(motivo_contenido, 0) + 1
                logger.warning("⚠️ Sin contenido (%s)", motivo_contenido)
                continue

            data = procesar_noticia(n["titulo"], contenido)
            data = normalizar_resultado_ia(data, n["titulo"])
            data["contenido_completo"] = contenido
            escribir_cache_ia(cache_ia, cache_key, data)
            cache_modificada = True
            time.sleep(1.2)

        # data ya viene normalizada: del cache (se guardó normalizada) o recién
        # procesada arriba.
        resultados.append({
            "diario": n["diario"],
            "titulo": n["titulo"],
            "evento": data["evento"],
            "resumen": data["resumen"],
            "enfoque": data.get("enfoque", ""),
            "contenido_completo": data.get("contenido_completo", ""),
            "link": n["link"],
            "categoria": n.get("categoria", "general")
        })

        logger.info("✅ OK")

    if cache_modificada:
        guardar_cache_ia(cache_ia)

    guardar_json_intermedio("processed_news.json", resultados)

    logger.info(
        "IA: %s procesadas, %s cache hits, %s cache misses, %s sin contenido",
        len(resultados), cache_hits, cache_misses, sin_contenido,
    )
    if fallos_contenido:
        logger.info("Fallos de contenido: %s", fallos_contenido)

    if not resultados:
        logger.error("❌ No hay resultados")
        return

    # 🔴 ETAPA 2: categorías
    categorias = {}

    for r in resultados:
        categorias.setdefault(normalizar_categoria(r["categoria"]), []).append(r)

    salida_final = ""
    noticias_web = []
    diagnostico_grupos = []

    # 🔴 ETAPA 3 y 4
    for categoria, lista in categorias.items():

        logger.info("📂 %s (%s noticias)", categoria.upper(), len(lista))

        res = agrupar_noticias(lista)

        if not res:
            logger.warning("No se pudo agrupar con IA; se publican las noticias separadas.")
            grupos = []
        else:
            grupos = parsear_grupos(res)

        grupos = depurar_grupos(lista, grupos)
        usados = {idx for grupo in grupos for idx in grupo}
        for idx in range(1, len(lista) + 1):
            if idx not in usados:
                grupos.append([idx])

        diagnostico_grupos.append(
            {
                "categoria": categoria,
                "cantidad_noticias": len(lista),
                "grupos": grupos,
            }
        )

        for grupo in grupos:
            eventos = []
            links = []

            for idx in grupo:
                if 1 <= idx <= len(lista):
                    item = lista[idx - 1]
                    eventos.append(
                        {
                            "medio": item["diario"],
                            "evento": item["evento"],
                            "resumen": item.get("resumen", ""),
                            "enfoque": item.get("enfoque", ""),
                        }
                    )
                    links.append(item["link"])

            texto = f"""
EVENTOS:
""" + "\n".join(
                [
                    (
                        f"- MEDIO: {item['medio']}\n"
                        f"  EVENTO: {item['evento']}\n"
                        f"  RESUMEN: {item['resumen']}\n"
                        f"  ENFOQUE: {item['enfoque']}"
                    )
                    for item in eventos
                ]
            ) + """

LINKS:
""" + "\n".join([f"- {l}" for l in links])

            final = unificar_bloques(texto)

            if final and len(final.strip()) > 30:
                salida_final += f"\nCATEGORIA: {categoria.upper()}\n"
                salida_final += final
                salida_final += "\n-----------------------------\n"
                noticia_web = extraer_noticia_unificada(categoria, final)
                if noticia_web:
                    noticias_web.append(noticia_web)

            if len(eventos) > 1:
                time.sleep(3)

    guardar_json_intermedio("groups.json", diagnostico_grupos)
    guardar_texto_intermedio("site_input.txt", salida_final)

    logger.info("--- OBTENIENDO DATOS FINANCIEROS ---")
    datos_financieros = get_datos_financieros()
    guardar_json_intermedio("financial_data.json", datos_financieros)
    logger.info("Datos financieros: %s indicadores", len(datos_financieros.get("indicadores", [])))

    logger.info("--- GENERANDO WEB ---")

    contenidos_completos = {r["link"]: r.get("contenido_completo", "") for r in resultados}
    generar_web(noticias_web, datos_financieros=datos_financieros, contenidos_completos=contenidos_completos)

    logger.info("🌐 Web generada: index.html")

    # 🔥 NUEVO: subida automática
    if publicar:
        subir_index_github()
    else:
        logger.info("Publicacion omitida. Usa --publish para hacer git push desde local.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera el resumen automatico de noticias.")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Despues de generar index.html, hace commit y push local.",
    )
    args = parser.parse_args()
    ejecutar_proyecto(publicar=args.publish)
