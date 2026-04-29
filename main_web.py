from scrapers import obtener_todo
from scrapers.utils import obtener_contenido
from ai import procesar_noticia
from analyzer import agrupar_noticias, depurar_grupos
from analyzer_2 import unificar_bloques

from web_generator import generar_web

import json
import os
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()

CACHE_IA_PATH = ".cache_ai.json"


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


def ejecutar_proyecto():
    print("\n--- INICIANDO RECOLECCIÓN DE NOTICIAS ---")

    noticias = obtener_todo()
    print(f"📰 Total noticias: {len(noticias)}")

    resultados = []
    cache_ia = cargar_cache_ia()
    cache_modificada = False

    # 🔴 ETAPA 1: IA
    for i, n in enumerate(noticias, start=1):
        print(f"\n🔎 [{i}/{len(noticias)}] {n['diario']}")
        print(f"📰 {n['titulo'][:80]}...")

        cache_key = n["link"]
        if cache_key in cache_ia:
            data = cache_ia[cache_key]
            print("✅ Cache IA")
        else:
            contenido = obtener_contenido(n["link"])

            if not contenido:
                print("⚠️ Sin contenido")
                continue

            data = procesar_noticia(n["titulo"], contenido)
            cache_ia[cache_key] = data
            cache_modificada = True
            time.sleep(1.2)

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

    if not resultados:
        print("❌ No hay resultados")
        return

    # 🔴 ETAPA 2: categorías
    categorias = {}

    for r in resultados:
        cat = r["categoria"].lower()

        if "eco" in cat:
            cat = "economia"
        elif "pol" in cat:
            cat = "politica"
        else:
            cat = "internacional"

        categorias.setdefault(cat, []).append(r)

    salida_final = ""

    # 🔴 ETAPA 3 y 4
    for categoria, lista in categorias.items():

        print(f"\n📂 {categoria.upper()} ({len(lista)} noticias)\n")

        res = agrupar_noticias(lista)

        if not res:
            continue

        grupos = parsear_grupos(res)
        grupos = depurar_grupos(lista, grupos)
        usados = {idx for grupo in grupos for idx in grupo}
        for idx in range(1, len(lista) + 1):
            if idx not in usados:
                grupos.append([idx])

        for grupo in grupos:
            eventos = []
            links = []

            for idx in grupo:
                if 1 <= idx <= len(lista):
                    item = lista[idx - 1]
                    eventos.append(item["evento"])
                    links.append(item["link"])

            texto = f"""
EVENTOS:
{" | ".join(eventos)}

LINKS:
""" + "\n".join([f"- {l}" for l in links])

            final = unificar_bloques(texto)

            if final and len(final.strip()) > 30:
                salida_final += f"\nCATEGORIA: {categoria.upper()}\n"
                salida_final += final
                salida_final += "\n-----------------------------\n"

            if len(eventos) > 1:
                time.sleep(3)

    print("\n--- GENERANDO WEB ---\n")

    generar_web(salida_final)

    print("🌐 Web generada: index.html")

    # 🔥 NUEVO: subida automática
    subir_index_github()


if __name__ == "__main__":
    ejecutar_proyecto()
