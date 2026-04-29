from scrapers import obtener_todo
from scrapers.utils import limpiar_titulo, obtener_contenido_detalle
from ai import procesar_noticia
from analyzer import agrupar_noticias, depurar_grupos
from analyzer_2 import unificar_bloques

from web_generator import generar_web
from groq_client import MODEL

import argparse
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CACHE_IA_PATH = ".cache_ai.json"
CACHE_IA_TTL_DIAS = int(os.getenv("CACHE_IA_TTL_DIAS", "3"))
CACHE_IA_VERSION = "evento-resumen-v2"
ARTIFACTS_DIR = Path("data")


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
        print(f"⚠️ No se pudo leer cache IA: {e}")
        return {}


def guardar_cache_ia(cache):
    try:
        with open(CACHE_IA_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ No se pudo guardar cache IA: {e}")


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
        print(f"No se pudo guardar {nombre}: {e}")


def guardar_texto_intermedio(nombre, texto):
    try:
        ARTIFACTS_DIR.mkdir(exist_ok=True)
        path = ARTIFACTS_DIR / nombre
        with open(path, "w", encoding="utf-8") as f:
            f.write(texto)
    except Exception as e:
        print(f"No se pudo guardar {nombre}: {e}")


def subir_index_github():
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("\nGitHub Actions se encarga del commit/push final.\n")
        return

    print("\n🚀 Subiendo index.html a GitHub...\n")

    try:
        subprocess.run(["git", "add", "index.html"], check=True)
        subprocess.run(["git", "commit", "-m", "update automatico"], check=False)
        subprocess.run(["git", "push"], check=True)

        print("✅ Web actualizada en GitHub Pages")

    except Exception as e:
        print("⚠️ Error subiendo a GitHub:", e)


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
                if idx not in usados:
                    grupo_actual.append(idx)
                    usados.add(idx)
            except:
                pass

    if grupo_actual:
        grupos.append(grupo_actual)

    return grupos


def normalizar_categoria(categoria):
    cat = (categoria or "general").lower()

    if "eco" in cat:
        return "economia"
    if "pol" in cat:
        return "politica"
    return "internacional"


def _texto_equivalente(a, b):
    return limpiar_titulo(a).lower() == limpiar_titulo(b).lower()


def normalizar_resultado_ia(data, titulo):
    if not isinstance(data, dict):
        data = {}

    evento = str(data.get("evento") or "").strip()
    resumen = str(data.get("resumen") or "").strip()

    evento = limpiar_titulo(evento or titulo[:120])
    resumen = limpiar_titulo(resumen or "")

    if not resumen or _texto_equivalente(resumen, evento) or _texto_equivalente(resumen, titulo):
        resumen = "El texto disponible no aporta detalles adicionales verificables sobre este hecho."

    return {"evento": evento, "resumen": resumen}


def ejecutar_proyecto(publicar=False):
    print("\n--- INICIANDO RECOLECCIÓN DE NOTICIAS ---")

    noticias = obtener_todo()
    guardar_json_intermedio("raw_news.json", noticias)
    print(f"📰 Total noticias: {len(noticias)}")

    resultados = []
    cache_ia = cargar_cache_ia()
    cache_modificada = False
    cache_hits = 0
    cache_misses = 0
    sin_contenido = 0
    fallos_contenido = {}

    # 🔴 ETAPA 1: IA
    for i, n in enumerate(noticias, start=1):
        print(f"\n🔎 [{i}/{len(noticias)}] {n['diario']}")
        print(f"📰 {n['titulo'][:80]}...")

        cache_key = n["link"]
        data = leer_cache_ia(cache_ia, cache_key)
        if data:
            cache_hits += 1
            print("✅ Cache IA")
        else:
            cache_misses += 1
            contenido, motivo_contenido = obtener_contenido_detalle(n["link"])

            if not contenido:
                sin_contenido += 1
                fallos_contenido[motivo_contenido] = fallos_contenido.get(motivo_contenido, 0) + 1
                print(f"⚠️ Sin contenido ({motivo_contenido})")
                continue

            data = procesar_noticia(n["titulo"], contenido)
            data = normalizar_resultado_ia(data, n["titulo"])
            escribir_cache_ia(cache_ia, cache_key, data)
            cache_modificada = True
            time.sleep(1.2)

        data = normalizar_resultado_ia(data, n["titulo"])

        resultados.append({
            "diario": n["diario"],
            "titulo": n["titulo"],
            "evento": data["evento"],
            "resumen": data["resumen"],
            "link": n["link"],
            "categoria": n.get("categoria", "general")
        })

        print("✅ OK")

    if cache_modificada:
        guardar_cache_ia(cache_ia)

    guardar_json_intermedio("processed_news.json", resultados)

    print(
        f"\nIA: {len(resultados)} procesadas, {cache_hits} cache hits, "
        f"{cache_misses} cache misses, {sin_contenido} sin contenido"
    )
    if fallos_contenido:
        print(f"Fallos de contenido: {fallos_contenido}")

    if not resultados:
        print("❌ No hay resultados")
        return

    # 🔴 ETAPA 2: categorías
    categorias = {}

    for r in resultados:
        categorias.setdefault(normalizar_categoria(r["categoria"]), []).append(r)

    salida_final = ""
    diagnostico_grupos = []

    # 🔴 ETAPA 3 y 4
    for categoria, lista in categorias.items():

        print(f"\n📂 {categoria.upper()} ({len(lista)} noticias)\n")

        res = agrupar_noticias(lista)

        if not res:
            print("No se pudo agrupar con IA; se publican las noticias separadas.")
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
                            "evento": item["evento"],
                            "resumen": item.get("resumen", ""),
                        }
                    )
                    links.append(item["link"])

            texto = f"""
EVENTOS:
""" + "\n".join(
                [
                    f"- EVENTO: {item['evento']}\n  RESUMEN: {item['resumen']}"
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

            if len(eventos) > 1:
                time.sleep(3)

    guardar_json_intermedio("groups.json", diagnostico_grupos)
    guardar_texto_intermedio("site_input.txt", salida_final)

    print("\n--- GENERANDO WEB ---\n")

    generar_web(salida_final)

    print("🌐 Web generada: index.html")

    # 🔥 NUEVO: subida automática
    if publicar:
        subir_index_github()
    else:
        print("Publicacion omitida. Usa --publish para hacer git push desde local.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera el resumen automatico de noticias.")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Despues de generar index.html, hace commit y push local.",
    )
    args = parser.parse_args()
    ejecutar_proyecto(publicar=args.publish)
