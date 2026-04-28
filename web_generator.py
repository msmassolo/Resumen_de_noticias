from datetime import datetime
import locale


def obtener_diario_y_clase(url):
    if "clarin.com" in url:
        return "Clarín", "clarin"
    elif "lanacion.com" in url:
        return "La Nación", "lanacion"
    elif "infobae.com" in url:
        return "Infobae", "infobae"
    elif "pagina12.com.ar" in url:
        return "Página 12", "pagina12"
    elif "ambito.com" in url:
        return "Ámbito", "ambito"
    else:
        return "Fuente", "default"


def generar_web(contenido):

    # Idioma fecha (FIX GitHub)
    try:
        locale.setlocale(locale.LC_TIME, "es_AR.UTF-8")
    except:
        try:
            locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
        except:
            locale.setlocale(locale.LC_TIME, "")

    fecha_actual = datetime.now()
    fecha_formateada = fecha_actual.strftime("%A %d de %B de %Y")
    hora_formateada = fecha_actual.strftime("%H:%M")

    bloques = contenido.split("CATEGORIA:")

    html_noticias = ""
    categoria_actual = None
    categorias_set = set()

    for bloque in bloques:
        if not bloque.strip():
            continue

        lineas = bloque.strip().split("\n")
        categoria = lineas[0].strip().upper()

        categorias_set.add(categoria)

        if categoria != categoria_actual:

            if categoria_actual is not None:
                html_noticias += "</section>"

            html_noticias += f"""
            <section class="categoria-section" data-categoria="{categoria}">
                <h2>{categoria}</h2>
            """

            categoria_actual = categoria

        titulo = ""
        resumen = ""
        links = []
        capturando_resumen = False

        for i, l in enumerate(lineas[1:], start=1):
            l_original = l
            l = l.strip()

            if l.startswith("TITULO:"):
                titulo = l.replace("TITULO:", "").strip()
                capturando_resumen = False

            elif l.startswith("RESUMEN:"):
                resumen = l.replace("RESUMEN:", "").strip()
                capturando_resumen = True

            elif l.startswith("LINKS:"):
                capturando_resumen = False

            elif l.startswith("- http"):
                links.append(l.replace("- ", "").strip())
                capturando_resumen = False

            elif capturando_resumen and l and not l.startswith("TITULO:") and not l.startswith("LINKS:") and "----" not in l:
                resumen += "\n" + l

            if "-----------------------------" in l:

                links = list(set(links))

                html_noticias += f"""
                <article class="card" data-categoria="{categoria}">
                    <h3>{titulo}</h3>
                    <p>{resumen}</p>
                    <div class="sources">
                """

                for link in links:
                    nombre, clase = obtener_diario_y_clase(link)

                    html_noticias += f"""
                        <a href="{link}" target="_blank" class="chip {clase}">
                            {nombre}
                        </a>
                    """

                html_noticias += """
                    </div>
                </article>
                """

                titulo = ""
                resumen = ""
                links = []

    if categoria_actual is not None:
        html_noticias += "</section>"

    filtros_html = '<div class="filtros">'
    for cat in sorted(categorias_set):
        filtros_html += f'<button class="filtro-btn" data-cat="{cat}">{cat}</button>'
    filtros_html += '</div>'

    html = """
    <html>
    <head>
        <title>Resumen de Noticias</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
            body {
                margin: 0;
                font-family: Arial;
                background: linear-gradient(-45deg, #fdf6f0, #f7f7fb, #f4f1ee, #fafafa);
                background-size: 400% 400%;
                animation: gradientBG 18s ease infinite;
            }

            @keyframes gradientBG {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            .header {
                text-align: center;
                padding: 40px;
            }

            .filtros {
                text-align: center;
                margin-bottom: 20px;
            }

            .filtro-btn {
                padding: 8px 12px;
                margin: 5px;
                border-radius: 20px;
                border: 1px solid #ccc;
                cursor: pointer;
                background: white;
            }

            .filtro-btn.active {
                background: black;
                color: white;
            }

            .container {
                max-width: 900px;
                margin: auto;
                padding: 20px;
            }

            .categoria-section h2 {
                text-align: center;
            }

            .card {
                background: white;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 10px;
            }

            .chip {
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 12px;
                margin-right: 5px;
                text-decoration: none;
            }

            .infobae { background:#fff3e6; color:#ff6a00; }
            .lanacion { background:#e6f0ff; color:#1a4ed8; }
            .clarin { background:#ffeaea; color:#d93025; }
        </style>
    </head>

    <body>

        <div class="header">
            <h1>📰 Resumen de Noticias</h1>
            <p>Edición __FECHA__ · __HORA__ hs</p>
        </div>

        __FILTROS__

        <div class="container">
            __NOTICIAS__
        </div>

    </body>
    </html>
    """

    html = html.replace("__FECHA__", fecha_formateada)
    html = html.replace("__HORA__", hora_formateada)
    html = html.replace("__FILTROS__", filtros_html)
    html = html.replace("__NOTICIAS__", html_noticias)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)