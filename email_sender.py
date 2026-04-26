import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def formatear_html(contenido):

    bloques = contenido.split("CATEGORIA:")

    html_final = ""
    categoria_actual = None

    for bloque in bloques:
        if not bloque.strip():
            continue

        lineas = bloque.strip().split("\n")

        categoria = lineas[0].strip().upper()

        # 🔥 Mostrar categoría SOLO si cambia
        if categoria != categoria_actual:
            html_final += f"""
            <div style="margin-top:30px;">
                <h3 style="
                    text-align:center;
                    font-size:16px;
                    font-weight:bold;
                    color:#333;
                    border-bottom:2px solid #eee;
                    padding-bottom:8px;
                ">
                    {categoria}
                </h3>
            </div>
            """
            categoria_actual = categoria

        titulo = ""
        resumen = ""
        links = []

        for l in lineas[1:]:
            l = l.strip()

            if l.startswith("TITULO:"):
                titulo = l.replace("TITULO:", "").strip()

            elif l.startswith("RESUMEN:"):
                resumen = l.replace("RESUMEN:", "").strip()

            elif l.startswith("- http"):
                links.append(l.replace("- ", "").strip())

            # 🔴 fin de noticia
            if "-----------------------------" in l:

                html_final += f"""
                <div style="
                    margin:15px 0;
                    padding:12px;
                    background:#fafafa;
                    border-radius:6px;
                ">
                    <p style="margin:5px 0;"><b>{titulo}</b></p>
                    <p style="margin:5px 0;"><b>{resumen}</b></p>
                """

                if links:
                    html_final += "<p style='margin:5px 0;'><b>Links:</b><br>"
                    for link in links:
                        html_final += f"""
                        <a href="{link}" style="color:#1a73e8; text-decoration:none;"><b>{link}</b></a><br>
                        """
                    html_final += "</p>"

                html_final += "</div>"

                # reset
                titulo = ""
                resumen = ""
                links = []

    return html_final


def enviar_email(contenido, remitente, password, destinatario):

    contenido_html = formatear_html(contenido)

    html = f"""
    <html>
    <body style="
        margin: 0;
        padding: 0;
        background-color: #f5f1e8;
        font-family: Arial, sans-serif;
    ">

        <div style="
            max-width: 650px;
            margin: 30px auto;
            background-color: #ffffff;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        ">

            <h2 style="
                text-align: center;
                margin-bottom: 25px;
                color: #1a73e8;
                font-size: 24px;
                font-weight: bold;
            ">
                📰 Resumen Inteligente de Noticias
            </h2>

            {contenido_html}

            <hr style="margin: 25px 0; border: none; border-top: 1px solid #ddd;">

            <p style="
                font-size: 12px;
                color: #888;
                text-align: center;
            ">
                Generado automáticamente
            </p>

        </div>

    </body>
    </html>
    """

    # 🔥 manejar múltiples destinatarios
    destinatarios = [d.strip() for d in destinatario.split(",")]

    msg = MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = "📰 Resumen diario de noticias"

    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(remitente, password)

        # 🔥 envío correcto a múltiples destinatarios
        server.sendmail(remitente, destinatarios, msg.as_string())
        server.quit()

        print("📧 Email enviado correctamente")

    except Exception as e:
        print(f"❌ Error enviando email: {e}")