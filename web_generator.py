from datetime import datetime
from html import escape
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


MEDIOS = {
    "clarin.com": ("Clarín", "clarin"),
    "lanacion.com": ("La Nación", "lanacion"),
    "infobae.com": ("Infobae", "infobae"),
    "pagina12.com.ar": ("Página 12", "pagina12"),
    "ambito.com": ("Ámbito", "ambito"),
}


def obtener_diario_y_clase(url):
    dominio = urlparse(url).netloc.lower()

    for dominio_medio, medio in MEDIOS.items():
        if dominio_medio in dominio:
            return medio

    return "Fuente", "default"


DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def formatear_fecha_es(fecha):
    dia = DIAS[fecha.weekday()]
    mes = MESES[fecha.month - 1]
    return f"{dia} {fecha.day:02d} de {mes} de {fecha.year}"


def normalizar_links(links):
    return list(dict.fromkeys(link for link in links if link.startswith(("http://", "https://"))))


def parsear_contenido(contenido):
    noticias = []
    categoria_actual = None
    noticia_actual = None
    capturando_resumen = False

    def guardar_noticia():
        nonlocal noticia_actual

        if not noticia_actual:
            return

        noticia_actual["links"] = normalizar_links(noticia_actual["links"])

        if noticia_actual["titulo"] or noticia_actual["resumen"] or noticia_actual["links"]:
            noticias.append(noticia_actual)

        noticia_actual = None

    for linea in contenido.splitlines():
        linea = linea.strip()

        if not linea:
            continue

        if linea.startswith("CATEGORIA:"):
            guardar_noticia()
            categoria_actual = linea.replace("CATEGORIA:", "", 1).strip().upper()
            capturando_resumen = False
            continue

        if linea.startswith("TITULO:"):
            guardar_noticia()
            noticia_actual = {
                "categoria": categoria_actual or "GENERAL",
                "titulo": linea.replace("TITULO:", "", 1).strip(),
                "resumen": "",
                "links": [],
            }
            capturando_resumen = False
            continue

        if noticia_actual is None:
            noticia_actual = {
                "categoria": categoria_actual or "GENERAL",
                "titulo": "",
                "resumen": "",
                "links": [],
            }

        if linea.startswith("RESUMEN:"):
            noticia_actual["resumen"] = linea.replace("RESUMEN:", "", 1).strip()
            capturando_resumen = True
        elif linea.startswith("LINKS:"):
            capturando_resumen = False
        elif linea.startswith("- http"):
            noticia_actual["links"].append(linea.replace("- ", "", 1).strip())
            capturando_resumen = False
        elif "-----------------------------" in linea:
            guardar_noticia()
            capturando_resumen = False
        elif capturando_resumen:
            noticia_actual["resumen"] = f"{noticia_actual['resumen']}\n{linea}".strip()

    guardar_noticia()
    return noticias


def normalizar_noticias(noticias):
    normalizadas = []

    for noticia in noticias or []:
        if not isinstance(noticia, dict):
            continue

        categoria = str(noticia.get("categoria") or "GENERAL").strip().upper()
        titulo = str(noticia.get("titulo") or "").strip()
        resumen = str(noticia.get("resumen") or "").strip()
        links = normalizar_links(noticia.get("links") or [])

        if not titulo and not resumen and not links:
            continue

        normalizadas.append(
            {
                "categoria": categoria,
                "titulo": titulo,
                "resumen": resumen,
                "links": links,
            }
        )

    return normalizadas


ORDEN_CATEGORIAS = ("ECONOMIA", "POLITICA", "INTERNACIONAL", "GENERAL")

NOMBRES_CATEGORIAS = {
    "ECONOMIA": "Economía",
    "POLITICA": "Política",
    "INTERNACIONAL": "Internacional",
    "GENERAL": "General",
}


def nombre_categoria(categoria):
    return NOMBRES_CATEGORIAS.get(categoria, categoria.title())


def ordenar_categorias(categorias):
    orden = {categoria: indice for indice, categoria in enumerate(ORDEN_CATEGORIAS)}
    return sorted(categorias, key=lambda categoria: (orden.get(categoria, len(orden)), categoria))


def clave_categoria(categoria):
    orden = {nombre: indice for indice, nombre in enumerate(ORDEN_CATEGORIAS)}
    return orden.get(categoria, len(orden)), categoria


def generar_html_noticias(noticias):
    html_noticias = ""
    categoria_actual = None

    for noticia in noticias:
        categoria = noticia["categoria"]

        if categoria != categoria_actual:
            if categoria_actual is not None:
                html_noticias += "</div></section>"

            total_categoria = sum(1 for item in noticias if item["categoria"] == categoria)

            html_noticias += f"""
            <section class="categoria-section" data-categoria="{escape(categoria)}">
                <div class="section-heading">
                    <h2>{escape(nombre_categoria(categoria))}</h2>
                    <span>{total_categoria} noticias</span>
                </div>
                <div class="news-grid">
            """
            categoria_actual = categoria

        texto_busqueda = " ".join(
            [
                noticia["titulo"],
                noticia["resumen"],
                " ".join(obtener_diario_y_clase(link)[0] for link in noticia["links"]),
            ]
        )

        html_noticias += f"""
                <article class="card" data-categoria="{escape(categoria)}" data-search="{escape(texto_busqueda, quote=True)}">
                    <h3>{escape(noticia["titulo"])}</h3>
                    <p>{escape(noticia["resumen"]).replace(chr(10), "<br>")}</p>
                    <div class="sources">
        """

        for link in noticia["links"]:
            nombre, clase = obtener_diario_y_clase(link)
            html_noticias += f"""
                        <a href="{escape(link, quote=True)}" target="_blank" rel="noopener noreferrer" class="chip {escape(clase)}">
                            Leer en {escape(nombre)}
                        </a>
            """

        html_noticias += """
                    </div>
                </article>
        """

    if categoria_actual is not None:
        html_noticias += "</div></section>"

    return html_noticias


def generar_filtros(categorias, conteos):
    total = sum(conteos.values())
    filtros_html = '<div class="filtros" aria-label="Filtros de categoría">'
    filtros_html += f'<button class="filtro-btn active" data-cat="TODAS" type="button">Todas <span>{total}</span></button>'

    for cat in ordenar_categorias(categorias):
        filtros_html += f'<button class="filtro-btn" data-cat="{escape(cat)}" type="button">{escape(nombre_categoria(cat))} <span>{conteos.get(cat, 0)}</span></button>'

    filtros_html += "</div>"
    return filtros_html


def normalizar_datos_financieros(datos):
    if not isinstance(datos, dict):
        return {"fuente": "Finanzas Argy", "url": "https://finanzasargy.com/", "indicadores": []}

    indicadores = []
    for item in datos.get("indicadores") or []:
        if not isinstance(item, dict):
            continue

        nombre = str(item.get("nombre") or "").strip()
        valor = str(item.get("valor") or "").strip()
        detalle = str(item.get("detalle") or "").strip()

        if not nombre or not valor:
            continue

        indicadores.append(
            {
                "nombre": nombre,
                "valor": valor,
                "detalle": detalle,
            }
        )

    return {
        "fuente": str(datos.get("fuente") or "Finanzas Argy").strip(),
        "url": str(datos.get("url") or "https://finanzasargy.com/").strip(),
        "indicadores": indicadores,
    }


def generar_html_datos_financieros(datos):
    datos = normalizar_datos_financieros(datos)
    indicadores = datos["indicadores"]

    if not indicadores:
        return ""

    items_html = ""
    for item in indicadores:
        detalle = f'<span>{escape(item["detalle"])}</span>' if item["detalle"] else ""
        items_html += f"""
                <article class="finance-card">
                    <span>{escape(item["nombre"])}</span>
                    <strong>{escape(item["valor"])}</strong>
                    {detalle}
                </article>
        """

    return f"""
        <section class="finance-section" aria-label="Datos financieros">
            <div class="finance-heading">
                <h2>Datos financieros</h2>
            </div>
            <div class="finance-grid">
                {items_html}
            </div>
            <p class="finance-source">
                Fuente:
                <a href="{escape(datos["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(datos["fuente"])}</a>
            </p>
        </section>
    """


def generar_web(contenido, output_path="index.html", datos_financieros=None):
    fecha_actual = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    fecha_formateada = formatear_fecha_es(fecha_actual)
    hora_formateada = fecha_actual.strftime("%H:%M")

    if isinstance(contenido, str):
        noticias = parsear_contenido(contenido)
    else:
        noticias = normalizar_noticias(contenido)

    noticias = sorted(noticias, key=lambda noticia: clave_categoria(noticia["categoria"]))
    categorias = {noticia["categoria"] for noticia in noticias}
    conteos = {categoria: sum(1 for noticia in noticias if noticia["categoria"] == categoria) for categoria in categorias}

    html_noticias = generar_html_noticias(noticias)
    filtros_html = generar_filtros(categorias, conteos)
    datos_financieros_html = generar_html_datos_financieros(datos_financieros)

    html = """
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Resumen de Noticias</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Inter:wght@600;700;800&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">

        <style>
            * {
                box-sizing: border-box;
            }

            :root {
                color-scheme: light;
                --background: #f6f3ec;
                --surface: #fffdf9;
                --surface-soft: #efe9db;
                --primary: #4d463c;
                --secondary: #ded4bc;
                --accent: #1f4b43;
                --accent-soft: #e4ece9;
                --text-primary: #211d16;
                --text-secondary: #6b6155;
                --border: #e2dcc9;
                --infobae: #D8B08C;
                --clarin: #C99999;
                --lanacion: #AEBFCF;
                --font-title: "Inter";
                --font-body: "IBM Plex Sans";
                --font-mono: "IBM Plex Mono";
                --shadow-card: 0 1px 2px rgba(33, 29, 22, 0.04), 0 10px 24px rgba(33, 29, 22, 0.05);
            }

            :root[data-theme="dark"] {
                color-scheme: dark;
                --background: #17140f;
                --surface: #1e1a13;
                --surface-soft: #262119;
                --primary: #c9c0ac;
                --secondary: #3a3327;
                --accent: #7fb7a6;
                --accent-soft: #24312c;
                --text-primary: #f2ede1;
                --text-secondary: #a89d88;
                --border: #322c22;
                --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.3), 0 12px 26px rgba(0, 0, 0, 0.28);
            }

            @media (prefers-color-scheme: dark) {
                :root:not([data-theme="light"]) {
                    color-scheme: dark;
                    --background: #17140f;
                    --surface: #1e1a13;
                    --surface-soft: #262119;
                    --primary: #c9c0ac;
                    --secondary: #3a3327;
                    --accent: #7fb7a6;
                    --accent-soft: #24312c;
                    --text-primary: #f2ede1;
                    --text-secondary: #a89d88;
                    --border: #322c22;
                    --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.3), 0 12px 26px rgba(0, 0, 0, 0.28);
                }
            }

            body {
                min-height: 100vh;
                margin: 0;
                color: var(--text-primary);
                background: var(--background);
                font-family: var(--font-body), "IBM Plex Sans";
                letter-spacing: 0;
                transition: background 200ms ease, color 200ms ease;
            }

            .header {
                text-align: left;
                padding: 30px 20px 14px;
                background: transparent;
                border-bottom: 1px solid var(--border);
            }

            .header-inner,
            .toolbar,
            .container {
                max-width: 1280px;
                margin: 0 auto;
            }

            .header-inner {
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                gap: 20px;
            }

            .header-copy {
                min-width: 0;
            }

            .eyebrow {
                margin: 0 0 8px;
                color: var(--accent);
                font-family: var(--font-mono), monospace;
                font-size: 10.5px;
                font-weight: 500;
                letter-spacing: 0.16em;
                text-transform: uppercase;
            }

            .header h1 {
                max-width: 820px;
                margin: 0;
                color: var(--text-primary);
                font-family: var(--font-title), "IBM Plex Sans", sans-serif;
                font-optical-sizing: auto;
                font-size: clamp(30px, 4vw, 52px);
                font-weight: 600;
                line-height: 1.06;
                letter-spacing: -0.01em;
            }

            .header p {
                max-width: 640px;
                margin: 10px 0 0;
                color: var(--text-secondary);
                font-size: 13.5px;
                line-height: 1.55;
            }

            .theme-toggle {
                display: inline-flex;
                align-items: center;
                gap: 7px;
                flex-shrink: 0;
                min-height: 34px;
                margin-bottom: 4px;
                padding: 0 13px;
                border: 1px solid var(--border);
                border-radius: 20px;
                color: var(--text-secondary);
                background: var(--surface);
                cursor: pointer;
                font-family: var(--font-mono), monospace;
                font-size: 10.5px;
                font-weight: 500;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                transition: border-color 160ms ease, color 160ms ease;
            }

            .theme-toggle:hover,
            .theme-toggle:focus-visible {
                border-color: var(--accent);
                color: var(--accent);
                outline: 0;
            }

            .toolbar {
                display: grid;
                grid-template-columns: minmax(240px, 1fr) auto;
                gap: 10px;
                padding: 16px 20px 10px;
            }

            .search-input {
                width: 100%;
                min-height: 38px;
                border: 1px solid var(--border);
                border-radius: 7px;
                padding: 0 14px;
                color: var(--text-primary);
                background: var(--surface);
                font-family: var(--font-body), "IBM Plex Sans";
                font-size: 13px;
                transition: border-color 160ms ease, background 160ms ease;
            }

            .search-input::placeholder {
                color: var(--text-secondary);
            }

            .search-input:focus,
            .compact-btn:focus-visible {
                border-color: var(--accent);
                outline: 0;
                background: var(--surface);
            }

            .compact-btn {
                min-height: 38px;
                border: 1px solid var(--border);
                border-radius: 7px;
                padding: 0 14px;
                color: var(--text-primary);
                background: var(--surface);
                cursor: pointer;
                font-family: var(--font-body), "IBM Plex Sans";
                font-size: 12px;
                font-weight: 600;
                transition: border-color 160ms ease, background 160ms ease;
            }

            .compact-btn:hover {
                border-color: var(--accent);
            }

            .filtros {
                justify-content: flex-start;
                max-width: 1280px;
                margin: 0 auto;
                padding: 4px 20px 18px;
                display: flex;
                flex-wrap: wrap;
                gap: 7px;
            }

            .filtro-btn {
                min-height: 30px;
                padding: 0 11px;
                border: 1px solid var(--border);
                border-radius: 20px;
                color: var(--text-secondary);
                background: var(--surface);
                cursor: pointer;
                font-family: var(--font-body), "IBM Plex Sans";
                font-size: 10.5px;
                font-weight: 600;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
            }

            .filtro-btn:hover,
            .filtro-btn:focus-visible {
                border-color: var(--accent);
                color: var(--text-primary);
                outline: 0;
            }

            .filtro-btn span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 19px;
                min-height: 19px;
                margin-left: 6px;
                border-radius: 999px;
                background: var(--surface-soft);
                color: var(--accent);
                font-size: 10px;
            }

            .filtro-btn.active {
                color: var(--surface);
                background: var(--accent);
                border-color: var(--accent);
            }

            .filtro-btn.active span {
                background: rgba(255, 255, 255, 0.22);
                color: var(--surface);
            }

            .container {
                padding: 2px 20px 42px;
            }

            .finance-section {
                max-width: 1280px;
                margin: 2px auto 8px;
                padding: 0 20px;
            }

            .finance-heading {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
                padding-bottom: 6px;
                border-bottom: 1px solid var(--border);
            }

            .finance-heading h2 {
                margin: 0;
                color: var(--text-primary);
                font-family: var(--font-title), "IBM Plex Sans", sans-serif;
                font-size: clamp(18px, 1.7vw, 23px);
                font-weight: 600;
                line-height: 1.15;
            }

            .finance-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 10px;
            }

            .finance-card {
                padding: 13px 14px;
                border: 1px solid var(--border);
                border-left: 3px solid var(--accent);
                border-radius: 8px;
                background: var(--surface);
            }

            .finance-card span {
                display: block;
                color: var(--text-secondary);
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .finance-card strong {
                display: block;
                margin-top: 5px;
                color: var(--text-primary);
                font-family: var(--font-mono), monospace;
                font-size: 19px;
                font-weight: 500;
                line-height: 1.15;
            }

            .finance-card strong + span {
                margin-top: 4px;
                color: var(--text-secondary);
                font-family: var(--font-body), "IBM Plex Sans";
                font-size: 11px;
                font-weight: 500;
                letter-spacing: 0;
                text-transform: none;
            }

            .finance-source {
                margin-top: 10px;
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 500;
            }

            .finance-source a {
                color: var(--accent);
                font-weight: 600;
                text-decoration: none;
            }

            .finance-source a:hover {
                text-decoration: underline;
            }

            .categoria-section {
                margin-top: 30px;
            }

            .section-heading {
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                gap: 12px;
                margin: 0 0 12px;
                padding-bottom: 8px;
                border-bottom: 2px solid var(--text-primary);
            }

            .section-heading h2 {
                margin: 0;
                text-align: left;
                color: var(--text-primary);
                font-family: var(--font-title), "IBM Plex Sans", sans-serif;
                font-size: clamp(20px, 2vw, 27px);
                font-weight: 600;
                line-height: 1.15;
            }

            .section-heading span {
                color: var(--text-secondary);
                font-family: var(--font-mono), monospace;
                font-size: 10px;
                font-weight: 500;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .news-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
            }

            .card {
                display: flex;
                flex-direction: column;
                min-height: 100%;
                margin: 0;
                padding: 16px;
                border: 1px solid var(--border);
                border-radius: 8px;
                background: var(--surface);
                box-shadow: var(--shadow-card);
                transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
            }

            .card:hover {
                border-color: var(--accent);
                transform: translateY(-2px);
            }

            .card h3 {
                margin: 0 0 8px;
                color: var(--text-primary);
                font-family: var(--font-title), "IBM Plex Sans", sans-serif;
                font-size: 17px;
                font-weight: 600;
                line-height: 1.28;
                letter-spacing: -0.005em;
                overflow-wrap: break-word;
                hyphens: none;
            }

            .card p {
                margin: 0 0 14px;
                color: var(--text-secondary);
                font-size: 12.5px;
                line-height: 1.55;
                overflow-wrap: break-word;
                hyphens: none;
            }

            .sources {
                margin-top: auto;
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }

            .chip {
                display: inline-flex;
                align-items: center;
                min-height: 23px;
                padding: 0 8px;
                border-radius: 5px;
                color: var(--text-primary);
                font-family: var(--font-body), "IBM Plex Sans";
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-decoration: none;
                text-transform: uppercase;
                transition: filter 160ms ease, transform 160ms ease;
            }

            .chip:hover {
                filter: saturate(1.1) brightness(0.96);
                transform: translateY(-1px);
            }

            .empty-state,
            .search-empty-state {
                display: none;
                max-width: 1280px;
                margin: 24px auto 0;
                padding: 14px 16px;
                border: 1px solid var(--border);
                border-radius: 8px;
                color: var(--text-secondary);
                background: var(--surface);
                text-align: center;
            }

            .search-results {
                display: none;
                max-width: 1280px;
                margin: 18px auto 0;
                padding: 0 20px 42px;
            }

            .search-results.is-active {
                display: block;
            }

            .search-results-heading {
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                gap: 12px;
                margin: 0 0 8px;
                padding-bottom: 6px;
                border-bottom: 1px solid var(--border);
            }

            .search-results-heading h2 {
                margin: 0;
                color: var(--text-primary);
                font-family: var(--font-title), "IBM Plex Sans", sans-serif;
                font-size: clamp(20px, 2vw, 27px);
                font-weight: 600;
                line-height: 1.15;
            }

            .search-results-heading span {
                color: var(--text-secondary);
                font-family: var(--font-mono), monospace;
                font-size: 10px;
                font-weight: 500;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .search-results-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
            }

            body.compact .card p {
                display: none;
            }

            body.compact .card {
                padding: 12px;
            }

            body.compact .card h3 {
                font-size: 14px;
            }

            .infobae { background: rgba(216, 176, 140, 0.56); color: #2b1c0d; }
            .clarin { background: rgba(201, 153, 153, 0.52); color: #2c1414; }
            .lanacion { background: rgba(174, 191, 207, 0.58); color: #16222f; }
            .pagina12 { background: rgba(203, 187, 165, 0.46); color: #241d10; }
            .ambito { background: rgba(178, 165, 138, 0.42); color: #241f10; }
            .default { background: var(--surface-soft); color: var(--text-primary); }

            @media (max-width: 1100px) {
                .news-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .search-results-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }

            @media (max-width: 760px) {
                .header {
                    padding: 22px 14px 14px;
                }

                .header-inner {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 12px;
                }

                .header h1 {
                    font-size: 30px;
                }

                .toolbar {
                    grid-template-columns: 1fr;
                    padding-left: 14px;
                    padding-right: 14px;
                }

                .filtros,
                .finance-section,
                .container {
                    padding-left: 14px;
                    padding-right: 14px;
                }

                .finance-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .news-grid {
                    grid-template-columns: 1fr;
                }

                .search-results {
                    padding-left: 14px;
                    padding-right: 14px;
                }

                .search-results-grid {
                    grid-template-columns: 1fr;
                }

                .section-heading {
                    align-items: flex-start;
                    flex-direction: column;
                    gap: 8px;
                }

                .card {
                    min-height: auto;
                    padding: 13px;
                }
            }

            .footer {
                max-width: 1280px;
                margin: 8px auto 0;
                padding: 0 20px 34px;
            }

            .footer-inner {
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(240px, 0.5fr);
                gap: 18px;
                padding-top: 18px;
                border-top: 1px solid var(--border);
            }

            .footer h2 {
                margin: 0;
                color: var(--text-primary);
                font-family: var(--font-title), "IBM Plex Sans", sans-serif;
                font-size: 20px;
                font-weight: 600;
                line-height: 1.15;
            }

            .footer p,
            .footer a {
                color: var(--text-secondary);
                font-size: 12px;
                line-height: 1.55;
            }

            .footer p {
                margin: 10px 0 0;
            }

            .footer a {
                display: block;
                text-decoration: none;
            }

            .footer a:hover {
                color: var(--text-primary);
            }

            @media (max-width: 760px) {
                .footer {
                    padding-left: 14px;
                    padding-right: 14px;
                }

                .footer-inner {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>

    <body>

        <div class="header">
            <div class="header-inner">
                <div class="header-copy">
                    <p class="eyebrow">Agente · Edición diaria</p>
                    <h1>Resumen de Noticias</h1>
                    <p>Actualizado el __FECHA__ a las __HORA__ hs. Las noticias más relevantes de economía, política e internacionales, resumidas para una lectura rápida y con acceso directo a cada nota para ampliar la información.</p>
                </div>
                <button class="theme-toggle" type="button" aria-pressed="false" aria-label="Cambiar entre modo claro y oscuro">
                    <span class="theme-toggle-label">Modo oscuro</span>
                </button>
            </div>
        </div>

        <div class="toolbar" aria-label="Herramientas de lectura">
            <input class="search-input" type="search" placeholder="Buscar en la edición" aria-label="Buscar noticias">
            <button class="compact-btn" type="button" aria-pressed="false">Modo compacto</button>
        </div>

        __FILTROS__

        __DATOS_FINANCIEROS__

        <main class="container">
            __NOTICIAS__
            <p class="empty-state">No hay noticias que coincidan con los filtros actuales.</p>
        </main>

        <section class="search-results" aria-label="Resultados de busqueda">
            <div class="search-results-heading">
                <h2>Resultados</h2>
                <span class="search-results-count"></span>
            </div>
            <div class="search-results-grid"></div>
            <p class="search-empty-state" style="display:none">No hay noticias que coincidan con tu búsqueda.</p>
        </section>

        <footer class="footer">
            <div class="footer-inner">
                <div>
                    <p class="eyebrow">Contacto</p>
                    <h2>Massolo Sebastian.</h2>
                </div>
                <div>
                    <a href="mailto:msmassolo@gmail.com">msmassolo@gmail.com</a>
                    <a href="https://www.linkedin.com/in/msmassolo/" target="_blank" rel="noopener noreferrer">linkedin.com/in/msmassolo</a>
                </div>
            </div>
        </footer>

        <script>
            const botonesFiltro = document.querySelectorAll(".filtro-btn");
            const secciones = document.querySelectorAll(".categoria-section");
            const buscador = document.querySelector(".search-input");
            const botonCompacto = document.querySelector(".compact-btn");
            const estadoVacio = document.querySelector(".empty-state");
            const estadoVacioBusqueda = document.querySelector(".search-empty-state");
            const contenedorPrincipal = document.querySelector(".container");
            const resultadosBusqueda = document.querySelector(".search-results");
            const grillaResultados = document.querySelector(".search-results-grid");
            const contadorResultados = document.querySelector(".search-results-count");
            let categoriaActiva = "TODAS";
            const cards = Array.from(document.querySelectorAll(".card")).map((card) => ({
                element: card,
                section: card.closest(".categoria-section"),
                category: card.dataset.categoria,
                search: normalizar(card.dataset.search || ""),
                originalParent: card.parentElement,
                placeholder: document.createComment("card-placeholder"),
            }));

            function normalizar(texto) {
                return texto.toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g, "");
            }

            function terminosBusqueda(valor) {
                return normalizar(valor)
                    .split(/\\s+/)
                    .map((termino) => termino.trim())
                    .filter((termino) => termino.length >= 2);
            }

            function aplicarFiltros() {
                const terminos = terminosBusqueda(buscador.value);
                const hayBusqueda = terminos.length > 0;
                let hayResultados = false;
                const visiblesPorSeccion = new Map();

                if (hayBusqueda) {
                    categoriaActiva = "TODAS";
                    botonesFiltro.forEach((item) => item.classList.remove("active"));
                    const todas = Array.from(botonesFiltro).find((item) => item.dataset.cat === "TODAS");
                    if (todas) todas.classList.add("active");

                    grillaResultados.innerHTML = "";
                    contenedorPrincipal.hidden = true;
                    resultadosBusqueda.classList.add("is-active");

                    cards.forEach(({ element, search, originalParent, placeholder }) => {
                        if (!placeholder.parentNode && element.parentNode === originalParent) {
                            originalParent.insertBefore(placeholder, element);
                        }

                        const visible = terminos.every((termino) => search.includes(termino));
                        element.hidden = !visible;

                        if (visible) {
                            grillaResultados.appendChild(element);
                            hayResultados = true;
                        } else if (placeholder.parentNode) {
                            placeholder.parentNode.insertBefore(element, placeholder.nextSibling);
                        }
                    });

                    contadorResultados.textContent = hayResultados
                        ? `${grillaResultados.children.length} noticias`
                        : "0 noticias";
                    if (estadoVacioBusqueda) {
                        estadoVacioBusqueda.style.display = hayResultados ? "none" : "block";
                    }
                    return;
                }

                resultadosBusqueda.classList.remove("is-active");
                grillaResultados.innerHTML = "";
                contenedorPrincipal.hidden = false;

                cards.forEach(({ element, originalParent, placeholder }) => {
                    if (placeholder.parentNode) {
                        originalParent.insertBefore(element, placeholder);
                        placeholder.remove();
                    }
                });

                cards.forEach(({ element, section, category, search }) => {
                    const coincideCategoria = categoriaActiva === "TODAS" || category === categoriaActiva;
                    const coincideBusqueda = terminos.length === 0 || terminos.every((termino) => search.includes(termino));
                    const visible = coincideCategoria && coincideBusqueda;

                    element.hidden = !visible;

                    if (visible) {
                        visiblesPorSeccion.set(section, (visiblesPorSeccion.get(section) || 0) + 1);
                        hayResultados = true;
                    }
                });

                secciones.forEach((seccion) => {
                    seccion.hidden = !visiblesPorSeccion.get(seccion);
                });

                estadoVacio.style.display = hayResultados ? "none" : "block";
            }

            botonesFiltro.forEach((boton) => {
                boton.addEventListener("click", () => {
                    categoriaActiva = boton.dataset.cat;

                    botonesFiltro.forEach((item) => item.classList.remove("active"));
                    boton.classList.add("active");

                    aplicarFiltros();
                });
            });

            buscador.addEventListener("input", () => {
                aplicarFiltros();
            });

            botonCompacto.addEventListener("click", () => {
                const activo = document.body.classList.toggle("compact");
                botonCompacto.setAttribute("aria-pressed", String(activo));
                botonCompacto.textContent = activo ? "Modo lectura" : "Modo compacto";
            });

            (function () {
                const CLAVE_TEMA = "tema-preferido";
                const raiz = document.documentElement;
                const botonTema = document.querySelector(".theme-toggle");
                const etiquetaTema = document.querySelector(".theme-toggle-label");
                const prefiereOscuro = window.matchMedia("(prefers-color-scheme: dark)");

                function temaEfectivo() {
                    const guardado = localStorage.getItem(CLAVE_TEMA);
                    if (guardado === "dark" || guardado === "light") return guardado;
                    return prefiereOscuro.matches ? "dark" : "light";
                }

                function aplicarTema(tema) {
                    raiz.setAttribute("data-theme", tema);
                    if (botonTema) botonTema.setAttribute("aria-pressed", String(tema === "dark"));
                    if (etiquetaTema) etiquetaTema.textContent = tema === "dark" ? "Modo claro" : "Modo oscuro";
                }

                aplicarTema(temaEfectivo());

                if (botonTema) {
                    botonTema.addEventListener("click", () => {
                        const nuevoTema = raiz.getAttribute("data-theme") === "dark" ? "light" : "dark";
                        localStorage.setItem(CLAVE_TEMA, nuevoTema);
                        aplicarTema(nuevoTema);
                    });
                }

                prefiereOscuro.addEventListener("change", (evento) => {
                    if (localStorage.getItem(CLAVE_TEMA)) return;
                    aplicarTema(evento.matches ? "dark" : "light");
                });
            })();
        </script>

    </body>
    </html>
    """

    html = html.replace("__FECHA__", escape(fecha_formateada))
    html = html.replace("__HORA__", escape(hora_formateada))
    html = html.replace("__FILTROS__", filtros_html)
    html = html.replace("__DATOS_FINANCIEROS__", datos_financieros_html)
    html = html.replace("__NOTICIAS__", html_noticias)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
