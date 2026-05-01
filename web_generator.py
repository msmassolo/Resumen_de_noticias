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
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">

        <style>
            * {
                box-sizing: border-box;
            }

            :root {
                color-scheme: light;
                --background: #F4F1EC;
                --surface: #E7DED1;
                --surface-soft: #DDD4C7;
                --primary: #B2A58A;
                --secondary: #CBBBA5;
                --accent: #8C7B6A;
                --text-primary: #2F2A24;
                --text-secondary: #5E564D;
                --border: #D8CFC3;
                --infobae: #D8B08C;
                --clarin: #C99999;
                --lanacion: #AEBFCF;
                --font-title: "Cormorant Garamond";
                --font-body: "Manrope";
            }

            body {
                min-height: 100vh;
                margin: 0;
                color: var(--text-primary);
                background:
                    radial-gradient(circle at 9% 8%, rgba(203, 187, 165, 0.26), transparent 28%),
                    radial-gradient(circle at 88% 4%, rgba(174, 191, 207, 0.18), transparent 30%),
                    var(--background);
                font-family: var(--font-body), "Manrope";
                letter-spacing: 0;
            }

            .header {
                text-align: left;
                padding: clamp(34px, 5vw, 62px) 24px 16px;
                background: transparent;
            }

            .header-inner,
            .toolbar,
            .container {
                max-width: 1180px;
                margin: 0 auto;
            }

            .eyebrow {
                margin: 0 0 12px;
                color: var(--accent);
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            }

            .header h1 {
                max-width: 820px;
                margin: 0;
                font-family: var(--font-title), "Cormorant Garamond";
                font-size: clamp(40px, 6vw, 76px);
                font-weight: 600;
                line-height: 0.98;
                letter-spacing: 0;
            }

            .header p {
                max-width: 760px;
                margin: 16px 0 0;
                color: var(--text-secondary);
                font-size: 14px;
                line-height: 1.72;
            }

            .toolbar {
                display: grid;
                grid-template-columns: minmax(240px, 1fr) auto;
                gap: 12px;
                padding: 18px 24px 8px;
            }

            .search-input {
                width: 100%;
                min-height: 46px;
                border: 1px solid var(--border);
                border-radius: 999px;
                padding: 0 20px;
                color: var(--text-primary);
                background: rgba(231, 222, 209, 0.46);
                font-family: var(--font-body), "Manrope";
                font-size: 14px;
                transition: border-color 160ms ease, background 160ms ease;
            }

            .search-input:focus,
            .compact-btn:focus-visible {
                border-color: var(--accent);
                outline: 0;
                background: rgba(231, 222, 209, 0.72);
            }

            .compact-btn {
                min-height: 46px;
                border: 1px solid var(--border);
                border-radius: 999px;
                padding: 0 20px;
                color: var(--text-primary);
                background: transparent;
                cursor: pointer;
                font-family: var(--font-body), "Manrope";
                font-size: 13px;
                font-weight: 700;
                transition: border-color 160ms ease, background 160ms ease;
            }

            .filtros {
                justify-content: flex-start;
                max-width: 1180px;
                margin: 0 auto;
                padding: 12px 24px 20px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }

            .filtro-btn {
                min-height: 40px;
                padding: 0 16px;
                border: 1px solid transparent;
                border-radius: 999px;
                color: var(--text-secondary);
                background: transparent;
                cursor: pointer;
                font-family: var(--font-body), "Manrope";
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
            }

            .filtro-btn:hover,
            .filtro-btn:focus-visible {
                border-color: var(--border);
                outline: 0;
            }

            .filtro-btn span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 24px;
                min-height: 24px;
                margin-left: 8px;
                border-radius: 999px;
                background: rgba(203, 187, 165, 0.26);
                color: var(--accent);
                font-size: 11px;
            }

            .filtro-btn.active {
                color: var(--text-primary);
                background: rgba(231, 222, 209, 0.72);
                border-color: var(--border);
            }

            .filtro-btn.active span {
                background: rgba(178, 165, 138, 0.32);
                color: var(--text-primary);
            }

            .container {
                padding: 4px 24px 64px;
            }

            .categoria-section {
                margin-top: clamp(28px, 5vw, 54px);
            }

            .section-heading {
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                gap: 18px;
                margin: 0 0 16px;
            }

            .section-heading h2 {
                margin: 0;
                text-align: left;
                color: var(--text-primary);
                font-family: var(--font-title), "Cormorant Garamond";
                font-size: clamp(28px, 3.4vw, 42px);
                font-weight: 600;
                line-height: 1;
            }

            .section-heading span {
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
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
                padding: 22px;
                border: 1px solid rgba(216, 207, 195, 0.72);
                border-radius: 24px;
                background: rgba(231, 222, 209, 0.34);
                box-shadow: 0 18px 46px rgba(47, 42, 36, 0.035);
                transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
            }

            .card:hover {
                border-color: rgba(140, 123, 106, 0.36);
                background: rgba(231, 222, 209, 0.48);
                transform: translateY(-2px);
            }

            .card.featured {
                grid-column: 1 / -1;
                min-height: 210px;
                padding: clamp(28px, 4vw, 42px);
                background: linear-gradient(135deg, rgba(231, 222, 209, 0.86), rgba(221, 212, 199, 0.48));
            }

            .card h3 {
                max-width: 880px;
                margin: 0 0 14px;
                color: var(--text-primary);
                font-family: var(--font-title), "Cormorant Garamond";
                font-size: clamp(23px, 2.35vw, 31px);
                font-weight: 600;
                line-height: 1.12;
                letter-spacing: 0;
                overflow-wrap: anywhere;
                hyphens: auto;
            }

            .card.featured h3 {
                font-size: clamp(32px, 4.2vw, 52px);
                line-height: 1.03;
            }

            .card p {
                max-width: 820px;
                margin: 0 0 20px;
                color: var(--text-secondary);
                font-size: 14px;
                line-height: 1.72;
            }

            .sources {
                margin-top: auto;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }

            .chip {
                display: inline-flex;
                align-items: center;
                min-height: 30px;
                padding: 0 11px;
                border-radius: 999px;
                color: var(--text-primary);
                font-family: var(--font-body), "Manrope";
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-decoration: none;
                text-transform: uppercase;
                transition: filter 160ms ease, transform 160ms ease;
            }

            .chip:hover {
                filter: saturate(1.04) brightness(0.98);
                transform: translateY(-1px);
            }

            .empty-state {
                display: none;
                max-width: 1180px;
                margin: 32px auto 0;
                padding: 22px 20px;
                border: 1px solid var(--border);
                border-radius: 24px;
                color: var(--text-secondary);
                background: rgba(231, 222, 209, 0.34);
                text-align: center;
            }

            body.compact .card p {
                display: none;
            }

            body.compact .card,
            body.compact .card.featured {
                padding: 20px;
            }

            body.compact .card h3,
            body.compact .card.featured h3 {
                font-size: clamp(22px, 2.6vw, 30px);
            }

            .infobae { background: rgba(216, 176, 140, 0.62); }
            .clarin { background: rgba(201, 153, 153, 0.58); }
            .lanacion { background: rgba(174, 191, 207, 0.64); }
            .pagina12 { background: rgba(203, 187, 165, 0.52); }
            .ambito { background: rgba(178, 165, 138, 0.48); }
            .default { background: rgba(221, 212, 199, 0.7); }

            @media (max-width: 820px) {
                .header {
                    padding: 34px 18px 14px;
                }

                .toolbar {
                    grid-template-columns: 1fr;
                    padding-left: 18px;
                    padding-right: 18px;
                }

                .filtros,
                .container {
                    padding-left: 18px;
                    padding-right: 18px;
                }

                .news-grid {
                    grid-template-columns: 1fr;
                }

                .section-heading {
                    align-items: flex-start;
                    flex-direction: column;
                    gap: 8px;
                }

                .card,
                .card.featured {
                    min-height: auto;
                    padding: 20px;
                    border-radius: 20px;
                }

                .card.featured h3 {
                    font-size: clamp(30px, 8vw, 44px);
                }
            }

            .footer {
                max-width: 1180px;
                margin: 18px auto 0;
                padding: 0 24px 54px;
            }

            .footer-inner {
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(240px, 0.5fr);
                gap: 24px;
                padding-top: 28px;
                border-top: 1px solid rgba(216, 207, 195, 0.86);
            }

            .footer h2 {
                margin: 0;
                font-family: var(--font-title), "Cormorant Garamond";
                font-size: clamp(28px, 3.2vw, 42px);
                font-weight: 600;
                line-height: 1;
            }

            .footer p,
            .footer a {
                color: var(--text-secondary);
                font-size: 13px;
                line-height: 1.8;
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

            @media (max-width: 820px) {
                .footer {
                    padding-left: 18px;
                    padding-right: 18px;
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
                <p class="eyebrow">Agente</p>
                <h1>Resumen de Noticias</h1>
                <p>Actualizado el __FECHA__ a las __HORA__ hs. Esta página permite una lectura rápida de los principales hechos de economía, política e internacionales, con la posibilidad de ingresar a cada noticia para acceder a los detalles si es requerido.</p>
            </div>
        </div>

        <div class="toolbar" aria-label="Herramientas de lectura">
            <input class="search-input" type="search" placeholder="Buscar en la edición" aria-label="Buscar noticias">
            <button class="compact-btn" type="button" aria-pressed="false">Modo compacto</button>
        </div>

        __FILTROS__

        <main class="container">
            __NOTICIAS__
            <p class="empty-state">No hay noticias que coincidan con los filtros actuales.</p>
        </main>

        <footer class="footer">
            <div class="footer-inner">
                <div>
                    <p class="eyebrow">Contacto</p>
                    <h2>Massolo Sebastian.</h2>
                </div>
                <div>
                    <a href="mailto:msmassolo@gmail.com">msmassolo@gmail.com</a>
                    <a href="mailto:sebastian.massolo@grupocepas.com">sebastian.massolo@grupocepas.com</a>
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
