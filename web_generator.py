html = f"""
<html>
<head>
    <meta charset="UTF-8">
    <title>Resumen de Noticias</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>

        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
            background: linear-gradient(-45deg, #fdf6f0, #f7f7fb, #f4f1ee, #fafafa);
            background-size: 400% 400%;
            animation: gradientBG 18s ease infinite;
            color: #222;
        }}

        @keyframes gradientBG {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}

        .header {{
            text-align: center;
            padding: 40px 20px 10px;
        }}

        .header h1 {{
            margin: 0;
            font-size: 36px;
            letter-spacing: -0.5px;
        }}

        .header p {{
            margin-top: 8px;
            font-size: 14px;
            opacity: 0.7;
        }}

        .filtros {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 20px 0 30px;
            flex-wrap: wrap;
        }}

        .filtro-btn {{
            padding: 10px 18px;
            border-radius: 999px;
            border: 1px solid #e0e0e0;
            background: rgba(255,255,255,0.8);
            backdrop-filter: blur(6px);
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.25s ease;
        }}

        .filtro-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        .filtro-btn.active {{
            background: #1a1a1a;
            color: white;
            border-color: #1a1a1a;
        }}

        .container {{
            max-width: 820px;
            margin: auto;
            padding: 0 20px 40px;
        }}

        .categoria-section {{
            margin-bottom: 40px;
            animation: fadeIn 0.4s ease;
        }}

        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .categoria-section h2 {{
            text-align: center;
            margin-bottom: 25px;
            letter-spacing: 1px;
        }}

        .card {{
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(8px);
            padding: 22px;
            border-radius: 16px;
            margin-bottom: 20px;
            border: 1px solid rgba(0,0,0,0.05);
            transition: all 0.25s ease;
        }}

        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 28px rgba(0,0,0,0.08);
        }}

        .card h3 {{
            margin-bottom: 10px;
            font-size: 19px;
            line-height: 1.35;
        }}

        .card p {{
            color: #555;
            line-height: 1.6;
        }}

        .sources {{
            margin-top: 14px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .chip {{
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .chip:hover {{
            transform: scale(1.05);
            opacity: 0.9;
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
        });
    </script>

</body>
</html>
"""