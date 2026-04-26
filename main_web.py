from scrapers import obtener_todo
from scrapers.utils import obtener_contenido
from ai import procesar_noticia
from analyzer import agrupar_noticias
from analyzer_2 import unificar_bloques

from web_generator import generar_web

import time
import subprocess
from dotenv import load_dotenv

load_dotenv()


# 🔥 NUEVO: función para subir a GitHub
def subir_index_github():
    print("\n🚀 Subiendo index.html a GitHub...\n")

    try:
        subprocess.run(["git", "add", "index.html"], check=True)
        subprocess.run(["git", "commit", "-m", "update automatico"], check=False)
        subprocess.run(["git", "push"], check=True)

        print("✅ Web actualizada en GitHub Pages")

    except Exception as e:
        print("⚠️ Error subiendo a GitHub:", e)


def parsear_grupos(texto):
    grupos = []
    grupo_actual = []

    for linea in texto.split("\n"):
        linea = linea.strip()

        if linea.startswith("GRUPO"):
            if grupo_actual:
                grupos.append(grupo_actual)
                grupo_actual = []

        elif linea.startswith("-"):
            try:
                idx = int(linea.replace("-", "").strip())
                grupo_actual.append(idx)
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

    # 🔴 ETAPA 1: IA
    for i, n in enumerate(noticias, start=1):
        print(f"\n🔎 [{i}/{len(noticias)}] {n['diario']}")
        print(f"📰 {n['titulo'][:80]}...")

        contenido = obtener_contenido(n["link"])

        if not contenido:
            print("⚠️ Sin contenido")
            continue

        data = procesar_noticia(n["titulo"], contenido)

        resultados.append({
            "diario": n["diario"],
            "titulo": n["titulo"],
            "evento": data["evento"],
            "resumen": data["resumen"],
            "link": n["link"],
            "categoria": n.get("categoria", "general")
        })

        print("✅ OK")
        time.sleep(1.2)

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

            time.sleep(3)

    print("\n--- GENERANDO WEB ---\n")

    generar_web(salida_final)

    print("🌐 Web generada: index.html")

    # 🔥 NUEVO: subida automática
    subir_index_github()


if __name__ == "__main__":
    ejecutar_proyecto()