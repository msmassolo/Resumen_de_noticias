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


ORDEN_CATEGORIAS = ("POLITICA", "ECONOMIA", "INTERNACIONAL", "GENERAL")


def ordenar_categorias(categorias):
    orden = {categoria: indice for indice, categoria in enumerate(ORDEN_CATEGORIAS)}
    return sorted(categorias, key=lambda categoria: (orden.get(categoria, len(orden)), categoria))


def clave_categoria(categoria):
    orden = {nombre: indice for indice, nombre in enumerate(ORDEN_CATEGORIAS)}
    return orden.get(categoria, len(orden)), categoria


def generar_html_noticias(noticias):
    html_noticias = ""
    categoria_actual = None
    indice_en_categoria = 0

    for noticia in noticias:
        categoria = noticia["categoria"]

        if categoria != categoria_actual:
            if categoria_actual is not None:
                html_noticias += "</div></section>"

            total_categoria = sum(1 for item in noticias if item["categoria"] == categoria)

            html_noticias += f"""
            <section class="categoria-section" data-categoria="{escape(categoria)}">
                <div class="section-heading">
                    <h2>{escape(categoria.title())}</h2>
                    <span>{total_categoria} noticias</span>
                </div>
                <div class="news-grid">
            """
            categoria_actual = categoria
            indice_en_categoria = 0

        indice_en_categoria += 1
        card_clase = "card featured" if indice_en_categoria == 1 else "card"

        html_noticias += f"""
                <article class="{card_clase}" data-categoria="{escape(categoria)}">
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
        filtros_html += f'<button class="filtro-btn" data-cat="{escape(cat)}" type="button">{escape(cat.title())} <span>{conteos.get(cat, 0)}</span></button>'

    filtros_html += "</div>"
    return filtros_html


def generar_web(contenido, output_path="index.html"):
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

    html = """
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Resumen de Noticias</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, Helvetica, sans-serif;
                color: #1f2933;
                background: linear-gradient(-45deg, #fdf6f0, #f7f7fb, #eef7f2, #fafafa);
                background-size: 400% 400%;
                animation: gradientBG 18s ease infinite;
            }

            @media (prefers-reduced-motion: reduce) {
                body {
                    animation: none;
                }
            }

            @keyframes gradientBG {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            .header {
                text-align: center;
                padding: 36px 20px 22px;
            }

            .header h1 {
                margin: 0 0 8px;
                font-size: clamp(28px, 5vw, 44px);
                line-height: 1.1;
            }

            .header p {
                margin: 0;
                color: #52616b;
            }

            .filtros {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 8px;
                max-width: 900px;
                margin: 0 auto 18px;
                padding: 0 20px;
            }

            .filtro-btn {
                min-height: 36px;
                padding: 8px 13px;
                border-radius: 999px;
                border: 1px solid #d3d8de;
                cursor: pointer;
                background: white;
                color: #1f2933;
                font: inherit;
                font-size: 14px;
            }

            .filtro-btn:hover,
            .filtro-btn:focus-visible {
                border-color: #111827;
                outline: none;
            }

            .filtro-btn.active {
                background: #111827;
                border-color: #111827;
                color: white;
            }

            .container {
                max-width: 900px;
                margin: auto;
                padding: 12px 20px 36px;
            }

            .categoria-section {
                margin-top: 20px;
            }

            .categoria-section[hidden],
            .card[hidden] {
                display: none;
            }

            .categoria-section h2 {
                text-align: center;
                margin: 22px 0 14px;
                font-size: 18px;
                letter-spacing: 0;
            }

            .card {
                background: rgba(255, 255, 255, 0.92);
                padding: 18px;
                margin-bottom: 14px;
                border: 1px solid rgba(214, 221, 230, 0.8);
                border-radius: 8px;
                box-shadow: 0 10px 24px rgba(31, 41, 51, 0.06);
            }

            .card h3 {
                margin: 0 0 10px;
                font-size: 20px;
                line-height: 1.25;
            }

            .card p {
                margin: 0 0 14px;
                line-height: 1.55;
                color: #374151;
            }

            .sources {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }

            .chip {
                display: inline-flex;
                align-items: center;
                min-height: 28px;
                padding: 5px 10px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 700;
                text-decoration: none;
            }

            .chip:hover {
                text-decoration: underline;
            }

            .infobae { background:#fff3e6; color:#b84c00; }
            .lanacion { background:#e6f0ff; color:#1a4ed8; }
            .clarin { background:#ffeaea; color:#b42318; }
            .pagina12 { background:#f1e8ff; color:#6d28d9; }
            .ambito { background:#e8f7ef; color:#047857; }
            .default { background:#edf2f7; color:#334155; }

            :root {
                color-scheme: light;
                --text: #172033;
                --muted: #637083;
                --line: #d8dee8;
                --surface: #ffffff;
                --soft: #f4f7fb;
                --accent: #0f766e;
                --accent-strong: #115e59;
            }

            body {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: var(--text);
                background: #f6f8fb;
                animation: none;
            }

            .header {
                text-align: left;
                padding: 34px 20px 24px;
                background: linear-gradient(180deg, #ffffff 0%, #eef4f7 100%);
                border-bottom: 1px solid var(--line);
            }

            .header-inner,
            .toolbar,
            .container {
                max-width: 1120px;
                margin: 0 auto;
            }

            .eyebrow {
                margin: 0 0 10px;
                color: var(--accent-strong);
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .header h1 {
                max-width: 760px;
                margin: 0;
                font-size: clamp(32px, 5vw, 54px);
                letter-spacing: 0;
            }

            .header p {
                max-width: 720px;
                margin-top: 12px;
                color: var(--muted);
                font-size: 16px;
            }

            .header .eyebrow {
                margin: 0 0 10px;
                color: var(--accent-strong);
                font-size: 12px;
            }

            .toolbar {
                display: grid;
                grid-template-columns: minmax(220px, 1fr) auto;
                gap: 12px;
                padding: 18px 20px 8px;
            }

            .search-input {
                width: 100%;
                min-height: 44px;
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 10px 13px;
                color: var(--text);
                background: var(--surface);
                font: inherit;
            }

            .search-input:focus,
            .compact-btn:focus-visible {
                border-color: var(--accent);
                outline: 3px solid rgba(15, 118, 110, 0.16);
            }

            .compact-btn {
                min-height: 44px;
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 0 14px;
                color: var(--text);
                background: var(--surface);
                cursor: pointer;
                font: inherit;
                font-weight: 700;
            }

            .filtros {
                justify-content: flex-start;
                max-width: 1120px;
                margin: 0 auto;
                padding: 8px 20px 16px;
            }

            .filtro-btn {
                border-radius: 8px;
                background: var(--surface);
                font-weight: 700;
            }

            .filtro-btn span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 22px;
                min-height: 22px;
                margin-left: 6px;
                border-radius: 999px;
                background: var(--soft);
                color: var(--muted);
                font-size: 12px;
            }

            .filtro-btn.active {
                background: var(--text);
                border-color: var(--text);
            }

            .filtro-btn.active span {
                background: rgba(255, 255, 255, 0.18);
                color: #ffffff;
            }

            .container {
                padding: 10px 20px 46px;
            }

            .categoria-section {
                margin-top: 30px;
            }

            .section-heading {
                display: flex;
                align-items: end;
                justify-content: space-between;
                gap: 12px;
                margin: 0 0 12px;
                padding-bottom: 10px;
                border-bottom: 1px solid var(--line);
            }

            .section-heading h2 {
                margin: 0;
                text-align: left;
                font-size: 18px;
            }

            .section-heading span {
                color: var(--muted);
                font-size: 13px;
                font-weight: 700;
            }

            .news-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
            }

            .card {
                display: flex;
                flex-direction: column;
                min-height: 100%;
                margin: 0;
                background: var(--surface);
                border-color: var(--line);
                box-shadow: none;
                transition: border-color 160ms ease, transform 160ms ease;
            }

            .card:hover {
                border-color: #aeb8c7;
                transform: translateY(-1px);
            }

            .card.featured {
                grid-column: 1 / -1;
                padding: 22px;
                border-top: 4px solid var(--accent);
            }

            .card h3 {
                font-size: 19px;
                letter-spacing: 0;
            }

            .card.featured h3 {
                font-size: clamp(24px, 3vw, 32px);
                line-height: 1.15;
            }

            .card p {
                color: #39465a;
            }

            .sources {
                margin-top: auto;
            }

            .chip {
                border-radius: 8px;
            }

            .empty-state {
                display: none;
                max-width: 1120px;
                margin: 24px auto 0;
                padding: 18px 20px;
                border: 1px dashed var(--line);
                border-radius: 8px;
                color: var(--muted);
                background: var(--surface);
                text-align: center;
            }

            body.compact .card p {
                display: none;
            }

            body.compact .card,
            body.compact .card.featured {
                padding: 16px;
            }

            body.compact .card h3,
            body.compact .card.featured h3 {
                font-size: 18px;
            }

            @media (max-width: 720px) {
                .toolbar {
                    grid-template-columns: 1fr;
                }

                .news-grid {
                    grid-template-columns: 1fr;
                }

                .section-heading {
                    align-items: flex-start;
                    flex-direction: column;
                }
            }

            :root {
                --text: #2f3440;
                --muted: #71798a;
                --line: #eadfea;
                --surface: #ffffff;
                --soft: #f7eef8;
                --page: #fff7fb;
                --accent: #b8dccc;
                --accent-strong: #5f8d80;
                --pink: #ffe3ec;
                --mint: #ddf4e8;
                --blue: #dfefff;
                --lavender: #ece5ff;
                --peach: #ffe8d6;
                --butter: #fff5c9;
            }

            body {
                color: var(--text);
                background:
                    radial-gradient(circle at top left, rgba(255, 227, 236, 0.72), transparent 34%),
                    radial-gradient(circle at top right, rgba(223, 239, 255, 0.74), transparent 32%),
                    linear-gradient(180deg, rgba(255,255,255,0.58), rgba(255,255,255,0)),
                    var(--page);
            }

            .header {
                padding: 30px 20px 18px;
                background: transparent;
                border-bottom: 0;
            }

            .eyebrow {
                color: var(--accent-strong);
                font-size: 11px;
                letter-spacing: 0.06em;
            }

            .header h1 {
                font-size: clamp(30px, 4vw, 46px);
                font-weight: 760;
            }

            .header p {
                color: var(--muted);
            }

            .toolbar {
                padding-top: 10px;
            }

            .search-input,
            .compact-btn,
            .filtro-btn,
            .card,
            .empty-state {
                border-color: var(--line);
                box-shadow: none;
            }

            .search-input,
            .compact-btn,
            .filtro-btn {
                background: rgba(255, 255, 255, 0.78);
            }

            .search-input:focus,
            .compact-btn:focus-visible,
            .filtro-btn:focus-visible {
                border-color: var(--accent);
                outline: 3px solid rgba(138, 182, 169, 0.22);
            }

            .compact-btn,
            .filtro-btn {
                font-weight: 650;
            }

            .filtro-btn.active {
                color: #4d7168;
                background: linear-gradient(180deg, #e2f4eb 0%, #f7eef8 100%);
                border-color: #c6e4d8;
            }

            .filtro-btn span,
            .filtro-btn.active span {
                color: var(--muted);
                background: rgba(255, 255, 255, 0.66);
            }

            .section-heading {
                border-bottom-color: rgba(225, 229, 238, 0.8);
            }

            .section-heading h2 {
                font-weight: 720;
            }

            .card {
                background: rgba(255, 255, 255, 0.76);
                border-radius: 8px;
            }

            .card:hover {
                border-color: #ccd6e3;
                transform: none;
            }

            .card.featured {
                border-top: 0;
                background: linear-gradient(135deg, #fff9e8 0%, #f3ecff 48%, #e9f7f1 100%);
            }

            .card h3 {
                color: #303642;
                font-weight: 730;
            }

            .card.featured h3 {
                font-size: clamp(23px, 3vw, 30px);
            }

            .card p {
                color: #555e6f;
            }

            .chip {
                color: #3b4452;
                border-radius: 8px;
                font-weight: 650;
            }

            .infobae { background: var(--peach); color: #9a5b2f; }
            .lanacion { background: var(--blue); color: #476b97; }
            .clarin { background: var(--pink); color: #9a5360; }
            .pagina12 { background: var(--lavender); color: #68558f; }
            .ambito { background: var(--mint); color: #4e7d62; }
            .default { background: #f1f3f6; color: #5e6876; }
        </style>
    </head>

    <body>

        <div class="header">
            <div class="header-inner">
                <p class="eyebrow">Panorama automático</p>
                <h1>Resumen de Noticias</h1>
                <p>Actualizado el __FECHA__ a las __HORA__ hs. Una vista rápida para leer, filtrar y abrir las fuentes principales.</p>
            </div>
        </div>

        <div class="toolbar" aria-label="Herramientas de lectura">
            <input class="search-input" type="search" placeholder="Buscar por título, resumen o fuente" aria-label="Buscar noticias">
            <button class="compact-btn" type="button" aria-pressed="false">Modo compacto</button>
        </div>

        __FILTROS__

        <main class="container">
            __NOTICIAS__
            <p class="empty-state">No hay noticias que coincidan con los filtros actuales.</p>
        </main>

        <script>
            const botonesFiltro = document.querySelectorAll(".filtro-btn");
            const secciones = document.querySelectorAll(".categoria-section");
            const buscador = document.querySelector(".search-input");
            const botonCompacto = document.querySelector(".compact-btn");
            const estadoVacio = document.querySelector(".empty-state");
            let categoriaActiva = "TODAS";

            function normalizar(texto) {
                return texto.toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g, "");
            }

            function aplicarFiltros() {
                const busqueda = normalizar(buscador.value.trim());
                let hayResultados = false;

                secciones.forEach((seccion) => {
                    const coincideCategoria = categoriaActiva === "TODAS" || seccion.dataset.categoria === categoriaActiva;
                    let visiblesEnSeccion = 0;

                    seccion.querySelectorAll(".card").forEach((card) => {
                        const coincideBusqueda = !busqueda || normalizar(card.textContent).includes(busqueda);
                        const visible = coincideCategoria && coincideBusqueda;

                        card.hidden = !visible;

                        if (visible) {
                            visiblesEnSeccion += 1;
                            hayResultados = true;
                        }
                    });

                    seccion.hidden = visiblesEnSeccion === 0;
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

            buscador.addEventListener("input", aplicarFiltros);

            botonCompacto.addEventListener("click", () => {
                const activo = document.body.classList.toggle("compact");
                botonCompacto.setAttribute("aria-pressed", String(activo));
                botonCompacto.textContent = activo ? "Modo lectura" : "Modo compacto";
            });
        </script>

    </body>
    </html>
    """

    html = html.replace("__FECHA__", escape(fecha_formateada))
    html = html.replace("__HORA__", escape(hora_formateada))
    html = html.replace("__FILTROS__", filtros_html)
    html = html.replace("__NOTICIAS__", html_noticias)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
