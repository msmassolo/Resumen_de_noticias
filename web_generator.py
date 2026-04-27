html = f"""
<html>
<head>
    <meta charset="UTF-8">
    <title>Resumen de Noticias</title>

    <style>

        body {{
            margin: 0;
            font-family: Arial;
            background: linear-gradient(-45deg, #fdf6f0, #f7f7fb, #f4f1ee, #fafafa);
            background-size: 400% 400%;
            animation: gradientBG 18s ease infinite;
        }}

        @keyframes gradientBG {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}

        .header {{
            text-align: center;
            padding: 40px;
        }}

        .header h1 {{
            margin: 0;
            font-size: 34px;
        }}

        .header p {{
            margin-top: 8px;
            color: #666;
        }}

        .filtros {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }}

        .filtro-btn {{
            padding: 10px 18px;
            border-radius: 999px;
            border: 1px solid #ddd;
            background: white;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s ease;
        }}

        .filtro-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        .filtro-btn.active {{
            background: #1a1a1a;
            color: white;
        }}

        .container {{
            max-width: 820px;
            margin: auto;
            padding: 20px;
        }}

        .categoria-section {{
            margin-bottom: 40px;
        }}

        .categoria-section h2 {{
            text-align: center;
            margin-bottom: 25px;
        }}

        .card {{
            background: white;
            padding: 20px;
            margin-bottom: 18px;
            border-radius: 12px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }}

        .card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 24px rgba(0,0,0,0.08);
        }}

        .card h3 {{
            margin-bottom: 10px;
        }}

        .card p {{
            color: #555;
            line-height: 1.6;
        }}

        .sources {{
            margin-top: 12px;
        }}

        .chip {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            margin-right: 6px;
            text-decoration: none;
        }}

        .infobae {{ background:#fff3e6; color:#ff6a00; }}
        .lanacion {{ background:#e6f0ff; color:#1a4ed8; }}
        .clarin {{ background:#ffeaea; color:#d93025; }}
        .pagina12 {{ background:#f0e6ff; color:#6b21a8; }}
        .ambito {{ background:#e6fff5; color:#047857; }}

    </style>
</head>

<body>

    <div class="header">
        <h1>📰 Resumen de Noticias</h1>
        <p>Edición {fecha_formateada} · {hora_formateada} hs</p>
    </div>

    {filtros_html}

    <div class="container">
        {html_noticias}
    </div>

    <script>
        const botones = document.querySelectorAll(".filtro-btn");
        const secciones = document.querySelectorAll(".categoria-section");

        let activa = null;

        botones.forEach(btn => {{
            btn.addEventListener("click", () => {{

                const categoria = btn.dataset.cat;

                if (activa === categoria) {{
                    activa = null;
                    botones.forEach(b => b.classList.remove("active"));
                    secciones.forEach(sec => sec.style.display = "block");
                    return;
                }}

                activa = categoria;

                botones.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                secciones.forEach(sec => {{
                    if (sec.dataset.categoria === categoria) {{
                        sec.style.display = "block";
                    }} else {{
                        sec.style.display = "none";
                    }}
                }});
            }});
        }});
    </script>

</body>
</html>
"""