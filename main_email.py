from scrapers import obtener_todo
from scrapers.utils import obtener_contenido
from ai import procesar_noticia
from analyzer import agrupar_noticias
from analyzer_2 import unificar_bloques
from email_sender import enviar_email

import time
import os
from dotenv import load_dotenv

load_dotenv()


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

    # 🔴 ETAPA 1: IA (evento + resumen)
    for i, n in enumerate(noticias, start=1):
        print(f"\n🔎 [{i}/{len(noticias)}] {n['diario']}")
        print(f"📰 {n['titulo'][:80]}...")

        contenido = obtener_contenido(n["link"])

        if not contenido:
            print("⚠️ Sin contenido")
            continue

        data = procesar_noticia(n["titulo"], contenido)

        evento = data["evento"]
        resumen = data["resumen"]

        # 🔥 DEBUG CLAVE
        print(f"🧠 EVENTO: {evento}")

        resultados.append({
            "diario": n["diario"],
            "titulo": n["titulo"],
            "evento": evento,
            "resumen": resumen,
            "link": n["link"],
            "categoria": n.get("categoria", "general")
        })

        print("✅ OK")

        time.sleep(1.2)

    if not resultados:
        print("❌ No hay resultados")
        return

    # 🔴 ETAPA 2: normalizar categorías
    print("\n🧠 Separando por categoría...\n")

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

    # 🔴 ETAPA 3: agrupación por evento
    for categoria, lista in categorias.items():

        print(f"\n📂 {categoria.upper()} ({len(lista)} noticias)\n")

        res = agrupar_noticias(lista)

        if not res:
            print("⚠️ Falló agrupación")
            continue

        grupos = parsear_grupos(res)

        bloques = []

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

            bloques.append(texto)

        # 🔴 ETAPA 4: redacción final
        for b in bloques:
            final = unificar_bloques(b)

            if final and len(final.strip()) > 30:

                # 🔥 FILTRO BASURA
                if "Resultados del Evento" in final:
                    print("⚠️ Bloque basura descartado")
                    continue

                salida_final += f"\nCATEGORIA: {categoria.upper()}\n"
                salida_final += final
                salida_final += "\n-----------------------------\n"

            else:
                print("⚠️ Falló generación final")

            time.sleep(5)

    print("\n--- RESULTADO FINAL ---\n")
    print(salida_final)

    print("\n📧 Enviando email...\n")

    enviar_email(
        salida_final,
        os.getenv("EMAIL_USER"),
        os.getenv("EMAIL_PASS"),
        os.getenv("EMAIL_TO")
    )


if __name__ == "__main__":
    ejecutar_proyecto()