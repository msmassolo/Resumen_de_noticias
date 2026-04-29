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


DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
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


def generar_html_noticias(noticias):
    html_noticias = ""
    categoria_actual = None

    for noticia in noticias:
        categoria = noticia["categoria"]

        if categoria != categoria_actual:
            if categoria_actual is not None:
                html_noticias += "</section>"

            html_noticias += f"""
            <section class="categoria-section" data-categoria="{escape(categoria)}">
                <h2>{escape(categoria)}</h2>
            """
            categoria_actual = categoria

        html_noticias += f"""
                <article class="card" data-categoria="{escape(categoria)}">
                    <h3>{escape(noticia["titulo"])}</h3>
                    <p>{escape(noticia["resumen"]).replace(chr(10), "<br>")}</p>
                    <div class="sources">
        """

        for link in noticia["links"]:
            nombre, clase = obtener_diario_y_clase(link)
            html_noticias += f"""
                        <a href="{escape(link, quote=True)}" target="_blank" rel="noopener noreferrer" class="chip {escape(clase)}">
                            {escape(nombre)}
                        </a>
            """

        html_noticias += """
                    </div>
                </article>
        """

    if categoria_actual is not None:
        html_noticias += "</section>"

    return html_noticias


def generar_filtros(categorias):
    filtros_html = '<div class="filtros" aria-label="Filtros de categoría">'
    filtros_html += '<button class="filtro-btn active" data-cat="TODAS" type="button">Todas</button>'

    for cat in sorted(categorias):
        filtros_html += f'<button class="filtro-btn" data-cat="{escape(cat)}" type="button">{escape(cat)}</button>'

    filtros_html += "</div>"
    return filtros_html


def generar_web(contenido, output_path="index.html"):
    fecha_actual = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    fecha_formateada = formatear_fecha_es(fecha_actual)
    hora_formateada = fecha_actual.strftime("%H:%M")

    noticias = parsear_contenido(contenido)
    categorias = {noticia["categoria"] for noticia in noticias}

    html_noticias = generar_html_noticias(noticias)
    filtros_html = generar_filtros(categorias)

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
        </style>
    </head>

    <body>

        <div class="header">
            <h1>Resumen de Noticias</h1>
            <p>Edición __FECHA__ · __HORA__ hs</p>
        </div>

        __FILTROS__

        <main class="container">
            __NOTICIAS__
        </main>

        <script>
            const botonesFiltro = document.querySelectorAll(".filtro-btn");
            const secciones = document.querySelectorAll(".categoria-section");

            botonesFiltro.forEach((boton) => {
                boton.addEventListener("click", () => {
                    const categoria = boton.dataset.cat;

                    botonesFiltro.forEach((item) => item.classList.remove("active"));
                    boton.classList.add("active");

                    secciones.forEach((seccion) => {
                        seccion.hidden = categoria !== "TODAS" && seccion.dataset.categoria !== categoria;
                    });
                });
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
