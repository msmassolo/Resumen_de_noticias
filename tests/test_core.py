import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

import analyzer_2
from main_web import extraer_noticia_unificada, normalizar_categoria, normalizar_resultado_ia, parsear_grupos
from scrapers.finanzas_argy import extraer_dolares, extraer_riesgo_pais, extraer_riesgo_pais_argentinadatos
from scrapers.infobae import _extraer_titulo_link
from scrapers.utils import limpiar_titulo, normalizar_url
from web_generator import (
    clave_categoria,
    generar_html_datos_financieros,
    generar_html_noticias,
    normalizar_noticias,
    parsear_contenido,
)


class CoreHelpersTest(unittest.TestCase):
    def test_normalizar_categoria_mapea_con_fallback_general(self):
        casos = {
            "economia": "economia",
            "Economía": "economia",
            "politica": "politica",
            "Política": "politica",
            "mundo": "internacional",
            "america": "internacional",
            "deportes": "general",
            "": "general",
            None: "general",
        }

        for entrada, esperada in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(normalizar_categoria(entrada), esperada)

    def test_parsear_grupos_json_filtra_indices_repetidos_e_invalidos(self):
        self.assertEqual(parsear_grupos("[[1, 2, 2], [0, 3], [4]]"), [[1, 2], [3], [4]])

    def test_parsear_grupos_formato_texto(self):
        texto = """
        GRUPO 1
        - 1
        - 2
        GRUPO 2
        - 2
        - 3
        """
        self.assertEqual(parsear_grupos(texto), [[1, 2], [3]])

    def test_extraer_noticia_unificada_devuelve_dict_limpio(self):
        bloque = """
        TITULO: Un hecho relevante
        RESUMEN: Primera linea.
        Segunda linea.
        LINKS:
        - https://example.com/a?utm_source=x
        - ftp://example.com/b
        - https://example.com/a?utm_source=x
        """
        self.assertEqual(
            extraer_noticia_unificada("politica", bloque),
            {
                "categoria": "POLITICA",
                "titulo": "Un hecho relevante",
                "resumen": "Primera linea.\nSegunda linea.",
                "links": ["https://example.com/a?utm_source=x"],
            },
        )

    def test_normalizar_url_resuelve_relativa_y_quita_tracking(self):
        url = normalizar_url(
            "https://www.infobae.com/politica/",
            "/politica/nota/?utm_source=x&id=7#comentarios",
        )
        self.assertEqual(url, "https://www.infobae.com/politica/nota/?id=7")

    def test_limpiar_titulo_separa_patrones_frecuentes(self):
        self.assertEqual(
            limpiar_titulo("Texto.PorAutor EN VIVO"),
            "Texto. Por Autor EN VIVO",
        )

    def test_infobae_prioriza_heading_para_no_pegar_bajada(self):
        html = """
        <a href="/economia/nota">
            <h2>Desde mañana las tarifas de colectivos aumentan 11,6 por ciento</h2>
            <h3>El gobierno provincial decidió un aumento superior</h3>
        </a>
        """
        link = BeautifulSoup(html, "html.parser").find("a")

        self.assertEqual(
            _extraer_titulo_link(link),
            "Desde mañana las tarifas de colectivos aumentan 11,6 por ciento",
        )

    def test_normalizar_resultado_ia_recorta_evento_con_bajada_pegada(self):
        titulo = "Desde mañana las tarifas de colectivos aumentan 11,6 por ciento"
        data = {
            "evento": f"{titulo} El gobierno provincial decidió un aumento superior",
            "resumen": "La provincia aplicará desde el lunes un aumento adicional.",
        }

        self.assertEqual(normalizar_resultado_ia(data, titulo)["evento"], titulo)

    def test_web_generator_acepta_texto_legado_y_datos_estructurados(self):
        texto = """
        CATEGORIA: POLITICA
        TITULO: Titulo
        RESUMEN: Resumen
        LINKS:
        - https://example.com/nota
        -----------------------------
        """
        self.assertEqual(
            parsear_contenido(texto),
            [
                {
                    "categoria": "POLITICA",
                    "titulo": "Titulo",
                    "resumen": "Resumen",
                    "links": ["https://example.com/nota"],
                }
            ],
        )

    def test_orden_categorias_prioriza_economia_politica_internacional(self):
        categorias = ["INTERNACIONAL", "POLITICA", "ECONOMIA"]
        self.assertEqual(sorted(categorias, key=clave_categoria), ["ECONOMIA", "POLITICA", "INTERNACIONAL"])

    def test_indice_busqueda_no_incluye_categoria(self):
        html = generar_html_noticias(
            [
                {
                    "categoria": "ECONOMIA",
                    "titulo": "Dolar financiero estable",
                    "resumen": "El mercado opero con bajo volumen.",
                    "links": ["https://www.infobae.com/economia/nota"],
                }
            ]
        )
        self.assertIn('data-search="Dolar financiero estable El mercado opero con bajo volumen. Infobae"', html)
        self.assertNotIn('data-search="ECONOMIA', html)

    def test_extraer_datos_financieros_desde_payloads(self):
        payload = {
            "data": {
                "panel": [
                    {"titulo": "Dólar Blue", "venta": "1400", "compra": "1380"},
                    {"titulo": "Dólar Oficial", "venta": "1415,80", "compra": "1363,46"},
                    {"titulo": "Dólar MEP", "venta": "1442,43", "compra": "1442,43"},
                ]
            }
        }
        html = 'commoditie&quot;:[0,&quot;Riesgo País&quot;],&quot;data&quot;:[0,{&quot;valor&quot;:[0,&quot;545&quot;],&quot;variacion&quot;:[0,&quot;-3,88%&quot;]}]'

        self.assertEqual([item["nombre"] for item in extraer_dolares(payload)], ["Dólar Blue", "Dólar Oficial", "Dólar MEP"])
        self.assertEqual(extraer_riesgo_pais(html)["valor"], "545")
        self.assertEqual(extraer_riesgo_pais(html)["detalle"], "-3,88%")

    def test_extraer_riesgo_pais_con_variacion_en_lineas_separadas(self):
        html = """
        <section>
            <span>Riesgo País</span>
            <strong>539,00</strong>
            <span>-4.94</span>
            <span>%</span>
        </section>
        """

        self.assertEqual(
            extraer_riesgo_pais(html),
            {
                "nombre": "Riesgo País",
                "valor": "539,00",
                "detalle": "-4.94%",
                "actualizado": "",
            },
        )

    def test_extraer_riesgo_pais_desde_argentinadatos(self):
        payload = [
            {"valor": 567, "fecha": "2026-04-30"},
            {"valor": 539, "fecha": "2026-05-01"},
        ]

        self.assertEqual(
            extraer_riesgo_pais_argentinadatos(payload),
            {
                "nombre": "Riesgo País",
                "valor": "539",
                "detalle": "",
                "actualizado": "2026-05-01",
            },
        )

    def test_generar_html_datos_financieros(self):
        html = generar_html_datos_financieros(
            {
                "fuente": "Finanzas Argy",
                "url": "https://finanzasargy.com/",
                "indicadores": [{"nombre": "Dólar Blue", "valor": "$ 1400", "detalle": "Compra $ 1380"}],
            }
        )

        self.assertIn("Datos financieros", html)
        self.assertIn("Dólar Blue", html)
        self.assertIn("Fuente:", html)
        self.assertIn('<a href="https://finanzasargy.com/"', html)
        self.assertNotIn("Ver fuente en", html)

    def test_unificar_bloques_incluye_contraste_por_medio_en_prompt(self):
        texto = """
        EVENTOS:
        - MEDIO: La Nación
          EVENTO: Cruces por una medida económica
          RESUMEN: El Gobierno defendió la medida ante críticas.
          ENFOQUE: Atribuye el conflicto a decisiones de Milei.
        - MEDIO: Clarín
          EVENTO: Cruces por una medida económica
          RESUMEN: La oposición cuestionó la aplicación de la medida.
          ENFOQUE: Vincula el conflicto con la presión opositora.

        LINKS:
        - https://example.com/lanacion
        - https://example.com/clarin
        """

        def fake_groq(_system, prompt, **_kwargs):
            self.assertIn("Medio: La Nación", prompt)
            self.assertIn("Atribuye el conflicto a decisiones de Milei", prompt)
            self.assertIn("Medio: Clarín", prompt)
            self.assertIn("presión opositora", prompt)
            self.assertIn("comparando por medio", prompt)
            return (
                '{"titulo":"Cruces por una medida económica",'
                '"resumen":"La Nación atribuye el conflicto a decisiones de Milei, '
                'mientras Clarín lo vincula con la presión opositora."}'
            )

        with patch.object(analyzer_2, "pedir_groq", side_effect=fake_groq):
            salida = analyzer_2.unificar_bloques(texto)

        self.assertIn("La Nación atribuye", salida)
        self.assertIn("Clarín lo vincula", salida)
        self.assertEqual(
            normalizar_noticias(
                [
                    {
                        "categoria": "politica",
                        "titulo": "Titulo",
                        "resumen": "Resumen",
                        "links": ["https://example.com/nota", "nope"],
                    }
                ]
            ),
            [
                {
                    "categoria": "POLITICA",
                    "titulo": "Titulo",
                    "resumen": "Resumen",
                    "links": ["https://example.com/nota"],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
