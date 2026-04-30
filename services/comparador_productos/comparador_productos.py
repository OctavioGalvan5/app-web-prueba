from datetime import datetime
from sqlalchemy import create_engine, text
from services.calculos import formatear_dinero, transformar_fecha
from xhtml2pdf import pisa
from io import BytesIO
from flask import render_template
import plotly.graph_objects as go
import io
import base64
from decimal import Decimal
from models.database import engine

# Configura tu engine

def obtener_precios(fecha_ingresada):
    """
    Obtiene los precios de la tabla 'precios' según la fecha más cercana pero no mayor a la ingresada.
    """
    # Convertir la fecha ingresada a un objeto datetime.date
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

    with engine.connect() as conn:
        # Ejecutar la consulta para obtener todas las filas de la tabla 'precios'
        result = conn.execute(text("SELECT * FROM precios"))

        # Variables para almacenar la fila más cercana
        fila_cercana = None
        fecha_cercana = None

        for row in result.mappings():  # Iterar sobre las filas como diccionarios
            fecha_fila = row['fecha']  # Acceder a la columna 'fecha' por nombre
            if fecha_fila <= fecha_ingresada_dt:
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = row

        if fila_cercana:
            # Extraer los valores usando nombres de columna
            leche_sachet = fila_cercana['leche_sachet']
            leche_polvo = fila_cercana['leche_polvo']
            pan_mesa = fila_cercana['pan_mesa']
            aceite_girasol = fila_cercana['aceite_girasol']
            arroz = fila_cercana['arroz']
            huevos = fila_cercana['huevos']
            harina = fila_cercana['harina']
            azucar = fila_cercana['azucar']
            cafe = fila_cercana['cafe']
            asado = fila_cercana['asado']
            link = fila_cercana['link']

            return leche_sachet, leche_polvo, pan_mesa, aceite_girasol, arroz, huevos, harina, azucar, cafe, asado, link
        else:
            return None

def crear_grafico(datos, nombre_grafico, etiquetas):
    valores = datos  # Usamos directamente los valores sin formatearlos

    # Encontrar el valor menor de los valores
    valor_minimo = min(valores)

    # Crear el gráfico
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
        marker_color=['#38225b', '#18488a', '#006faf', '#0096c6', '#7E7F9C', '#00bccb', '#00e0c4'],
        text=valores,  # Usamos los valores directamente para el texto
        textposition='auto',
        textfont=dict(size=14)
    ))

    # Agregar línea roja horizontal al nivel del valor mínimo
    fig.add_shape(
        type='line',
        x0=-0.5,  # Extiende la línea desde antes de la primera barra
        x1=len(etiquetas) - 0.5,  # Hasta después de la última barra
        y0=valor_minimo,  # Altura del valor mínimo
        y1=valor_minimo,
        line=dict(color='red', width=3, dash='dash')
    )

    # Actualizar el diseño del gráfico
    fig.update_layout(
        title=nombre_grafico, 
        xaxis_title='Fechas a comparar', 
        yaxis_title='Cantidad de Productos',
        plot_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del área de trazado transparente
        paper_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del gráfico transparente
        margin=dict(l=40, r=40, t=40, b=40),
        width=800, height=400,
        xaxis=dict(title_font=dict(size=14), tickfont=dict(size=12)),
        yaxis=dict(title_font=dict(size=14), tickfont=dict(size=12))
    )

    # Guardar el gráfico como imagen en un buffer
    img_bytes = fig.to_image(format="png")  # Usar Kaleido para generar la imagen

    # Codificar la imagen en base64
    grafico_base64 = base64.b64encode(img_bytes).decode('utf-8')

    return grafico_base64


class Comparador_productos:
    def __init__(self, autos, expediente, primer_haber_reclamado, primer_fecha, segundo_haber_reclamado, segunda_fecha):
        self.autos = autos
        self.expediente = expediente
        self.primer_haber_reclamado = primer_haber_reclamado
        self.primer_fecha = primer_fecha
        self.segundo_haber_reclamado = segundo_haber_reclamado
        self.segunda_fecha = segunda_fecha

    def obtener_datos(self):
        (leche_sachet_1, leche_polvo_1, pan_mesa_1, aceite_girasol_1, arroz_1, huevos_1, harina_1, azucar_1, cafe_1,asado_1, link_1) = obtener_precios(self.primer_fecha)

        (leche_sachet_2, leche_polvo_2, pan_mesa_2, aceite_girasol_2, arroz_2, huevos_2, harina_2, azucar_2, cafe_2,asado_2, link_2) = obtener_precios(self.segunda_fecha)

        datos = {}

        datos['autos'] = self.autos
        datos['expediente'] = self.expediente
        datos['primer_haber_reclamado'] = self.primer_haber_reclamado
        datos['primer_fecha'] = transformar_fecha(self.primer_fecha)
        datos['segundo_haber_reclamado'] = self.segundo_haber_reclamado
        datos['segunda_fecha'] = transformar_fecha(self.segunda_fecha)

        datos['leche_sachet_1'] = formatear_dinero(leche_sachet_1)
        datos['leche_polvo_1'] = formatear_dinero(leche_polvo_1)
        datos['pan_mesa_1'] = formatear_dinero(pan_mesa_1)
        datos['aceite_girasol_1'] = formatear_dinero(aceite_girasol_1)
        datos['arroz_1'] = formatear_dinero(arroz_1)
        datos['huevos_1'] = formatear_dinero(huevos_1)
        datos['harina_1'] = formatear_dinero(harina_1)
        datos['azucar_1'] = formatear_dinero(azucar_1)
        datos['cafe_1'] = formatear_dinero(cafe_1)
        datos['asado_1'] = formatear_dinero(asado_1)
        datos['link_1'] = link_1  # Los links no necesitan formateo de dinero

        datos['leche_sachet_2'] = formatear_dinero(leche_sachet_2)
        datos['leche_polvo_2'] = formatear_dinero(leche_polvo_2)
        datos['pan_mesa_2'] = formatear_dinero(pan_mesa_2)
        datos['aceite_girasol_2'] = formatear_dinero(aceite_girasol_2)
        datos['arroz_2'] = formatear_dinero(arroz_2)
        datos['huevos_2'] = formatear_dinero(huevos_2)
        datos['harina_2'] = formatear_dinero(harina_2)
        datos['azucar_2'] = formatear_dinero(azucar_2)
        datos['cafe_2'] = formatear_dinero(cafe_2)
        datos['asado_2'] = formatear_dinero(asado_2)
        datos['link_2'] = link_2  # Los links no necesitan formateo de dinero


        datos['cantidad_leche_1'] = round(Decimal(self.primer_haber_reclamado) / leche_sachet_1, 2)
        datos['cantidad_leche_2'] = round(Decimal(self.segundo_haber_reclamado) / leche_sachet_2, 2)
        datos['cantidad_leche_polvo_1'] = round(Decimal(self.primer_haber_reclamado) / leche_polvo_1, 2)
        datos['cantidad_leche_polvo_2'] = round(Decimal(self.segundo_haber_reclamado) / leche_polvo_2, 2)
        datos['cantidad_pan_mesa_1'] = round(Decimal(self.primer_haber_reclamado) / pan_mesa_1, 2)
        datos['cantidad_pan_mesa_2'] = round(Decimal(self.segundo_haber_reclamado) / pan_mesa_2, 2)
        datos['cantidad_aceite_girasol_1'] = round(Decimal(self.primer_haber_reclamado) / aceite_girasol_1, 2)
        datos['cantidad_aceite_girasol_2'] = round(Decimal(self.segundo_haber_reclamado) / aceite_girasol_2, 2)
        datos['cantidad_arroz_1'] = round(Decimal(self.primer_haber_reclamado) / arroz_1, 2)
        datos['cantidad_arroz_2'] = round(Decimal(self.segundo_haber_reclamado) / arroz_2, 2)
        datos['cantidad_huevos_1'] = round(Decimal(self.primer_haber_reclamado) / huevos_1, 2)
        datos['cantidad_huevos_2'] = round(Decimal(self.segundo_haber_reclamado) / huevos_2, 2)
        datos['cantidad_harina_1'] = round(Decimal(self.primer_haber_reclamado) / harina_1, 2)
        datos['cantidad_harina_2'] = round(Decimal(self.segundo_haber_reclamado) / harina_2, 2)
        datos['cantidad_azucar_1'] = round(Decimal(self.primer_haber_reclamado) / azucar_1, 2)
        datos['cantidad_azucar_2'] = round(Decimal(self.segundo_haber_reclamado) / azucar_2, 2)
        datos['cantidad_cafe_1'] = round(Decimal(self.primer_haber_reclamado) / cafe_1, 2)
        datos['cantidad_cafe_2'] = round(Decimal(self.segundo_haber_reclamado) / cafe_2, 2)
        datos['cantidad_asado_1'] = round(Decimal(self.primer_haber_reclamado) / asado_1, 2)
        datos['cantidad_asado_2'] = round(Decimal(self.segundo_haber_reclamado) / asado_2, 2)


        datos['media_1'] = (
            datos['cantidad_leche_1'] +
            datos['cantidad_leche_polvo_1'] +
            datos['cantidad_pan_mesa_1'] +
            datos['cantidad_aceite_girasol_1'] +
            datos['cantidad_arroz_1'] +
            datos['cantidad_huevos_1'] +
            datos['cantidad_harina_1'] +
            datos['cantidad_azucar_1'] +
            datos['cantidad_cafe_1'] +
            datos['cantidad_asado_1']
        )
        datos['media_2'] = (
            datos['cantidad_leche_2'] +
            datos['cantidad_leche_polvo_2'] +
            datos['cantidad_pan_mesa_2'] +
            datos['cantidad_aceite_girasol_2'] +
            datos['cantidad_arroz_2'] +
            datos['cantidad_huevos_2'] +
            datos['cantidad_harina_2'] +
            datos['cantidad_azucar_2'] +
            datos['cantidad_cafe_2'] +
            datos['cantidad_asado_2']
        )

        datos['perdida_poder_adquisitivo'] = round(-(1-datos['media_1']/datos['media_2'])*100, 2)
        datos['primer_haber_reclamado'] = formatear_dinero(self.primer_haber_reclamado)
        datos['segundo_haber_reclamado'] = formatear_dinero(self.segundo_haber_reclamado)

        return datos

    def generar_pdf(self):
        datos = self.obtener_datos()

        datos_grafico = [datos['media_1'], datos['media_2']]
        etiquetas_grafico = [datos['primer_fecha'], datos['segunda_fecha']]

        grafico = crear_grafico(datos_grafico, 'Comparación de Poder Adquisitivo', etiquetas_grafico)


        rendered = render_template(
            'comparador_productos/resultado.html', datos=datos, grafico=grafico
        )

        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
