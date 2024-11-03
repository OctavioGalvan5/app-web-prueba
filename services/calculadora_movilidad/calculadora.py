import plotly.graph_objects as go
import io
import base64
from services.calculos import formatear_dinero, transformar_fecha
from models.database import buscar_fechas
from flask import render_template, send_file
from werkzeug.wrappers import response
from config import config
from xhtml2pdf import pisa
from io import BytesIO

def crear_graficos(datos, etiquetas):
    etiquetas = etiquetas
    valores = datos
    resultados = list(map(formatear_dinero, valores))
    # Crear el gráfico
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
         marker_color=['#7671FA','#00c4ff', '#E5EAF3', '#07244C', '#178DAD', '#7E7F9C', '#9e73a3', '#3cd7c4'],
        text=resultados, textposition='auto',
        textfont=dict(size=14)

    ))

    # Actualizar el diseño del gráfico
    fig.update_layout(
        title='', 
        xaxis_title='', 
        yaxis_title='',
        plot_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del área de trazado transparente
        paper_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del gráfico transparente
        margin=dict(l=40, r=40, t=40, b=40),
        width=800, height=400,
        xaxis=dict(title_font=dict(size=14), tickfont=dict(size=10)),
        yaxis=dict(title_font=dict(size=14), tickfont=dict(size=15))
    )

    # Guardar el gráfico como imagen en un buffer
    img_bytes = fig.to_image(format="png")  # Usar Kaleido para generar la imagen

    # Codificar la imagen en base64
    grafico_base64 = base64.b64encode(img_bytes).decode('utf-8')

    return grafico_base64

class CalculadorMovilidad:
    def __init__(self, datos_del_actor, expediente, beneficio, fecha_inicio, fecha_fin, fecha_adquisicion_del_derecho, monto, ipc, ripte, uma, movilidad_sentencia, Ley_27426_rezago, Caliva_mas_anses, comparacion_mov_sentencia_si, comparacion_mov_sentencia_no ):
        self.datos_del_actor = datos_del_actor
        self.expediente = expediente
        self.beneficio = beneficio
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.fecha_adquisicion_del_derecho = fecha_adquisicion_del_derecho
        self.monto = monto
        self.ipc = ipc
        self.ripte = ripte
        self.uma = uma
        self.movilidad_sentencia = movilidad_sentencia
        self.Ley_27426_rezago = Ley_27426_rezago
        self.Caliva_mas_anses = Caliva_mas_anses
        self.comparacion_mov_sentencia_si = comparacion_mov_sentencia_si
        self.comparacion_mov_sentencia_no = comparacion_mov_sentencia_no

    def obtener_datos(self):
        lista_filas, lista_montos = buscar_fechas(self.fecha_inicio,self.fecha_fin, self.monto)
        ultimos_valores = lista_montos[-1]
        diccionario_comparacion = {
               'dif_anses_ipc': formatear_dinero(ultimos_valores[1] - ultimos_valores[0]),
               'conf_anses_ipc': str(round((ultimos_valores[1] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_ipc': formatear_dinero(ultimos_valores[1] - ultimos_valores[4]),
               'conf_sent_ipc': str(round((ultimos_valores[1] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
               #
               'dif_anses_ripte': formatear_dinero(ultimos_valores[2] - ultimos_valores[0]),
               'conf_anses_ripte': str(round((ultimos_valores[2] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_ripte': formatear_dinero(ultimos_valores[2] - ultimos_valores[4]),
               'conf_sent_ripte': str(round((ultimos_valores[2] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
                #
               'dif_anses_UMA': formatear_dinero(ultimos_valores[3] - ultimos_valores[0]),
               'conf_anses_UMA': str(round((ultimos_valores[3] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_UMA': formatear_dinero(ultimos_valores[3] - ultimos_valores[4]),
               'conf_sent_UMA': str(round((ultimos_valores[3] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
                #
               'dif_anses_sent': formatear_dinero(ultimos_valores[4] - ultimos_valores[0]),
               'conf_anses_sent': str(round((ultimos_valores[4] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
                #
               'dif_anses_ley27426': formatear_dinero(ultimos_valores[5] - ultimos_valores[0]),
               'conf_anses_ley27426': str(round((ultimos_valores[5] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_ley27426': formatear_dinero(ultimos_valores[5] - ultimos_valores[4]),
               'conf_sent_ley27426': str(round((ultimos_valores[5] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
                #
                'dif_anses_caliva_mas_anses': formatear_dinero(ultimos_valores[6] - ultimos_valores[0]),
                'conf_anses_caliva_mas_anses': str(round((ultimos_valores[6] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
                'dif_sent_caliva_mas_anses': formatear_dinero(ultimos_valores[6] - ultimos_valores[4]),
                'conf_sent_caliva_mas_anses': str(round((ultimos_valores[6] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%"
           }
        datos = []
        etiquetas = []
        if self.ipc:
            datos.append(round(ultimos_valores[1] - ultimos_valores[0],2))
            etiquetas.append('IPC')
        if self.ripte:
            datos.append(round(ultimos_valores[2] - ultimos_valores[0],2))
            etiquetas.append('RIPTE')
        if self.uma:
            datos.append(round(ultimos_valores[3] - ultimos_valores[0],2))
            etiquetas.append('UMA')
        if self.movilidad_sentencia:
            datos.append(round(ultimos_valores[4] - ultimos_valores[0],2))
            etiquetas.append('Movilidad de Sentencia')
        if self.Ley_27426_rezago:
            datos.append(round(ultimos_valores[5] - ultimos_valores[0],2))
            etiquetas.append('Ley 27426 con rezago')
        if self.Caliva_mas_anses:
            datos.append(round(ultimos_valores[6] - ultimos_valores[0],2))
            etiquetas.append('Caliva mas Anses')
        grafico1 = crear_graficos(datos,etiquetas)

        if self.comparacion_mov_sentencia_si:
            datos_2 = []
            etiquetas_2 = []
            if self.ipc:
                datos_2.append(round(ultimos_valores[1] - ultimos_valores[4],2))
                etiquetas_2.append('IPC')
            if self.ripte:
                datos_2.append(round(ultimos_valores[2] - ultimos_valores[4],2))
                etiquetas_2.append('RIPTE')
            if self.uma:
                datos_2.append(round(ultimos_valores[3] - ultimos_valores[4],2))
                etiquetas_2.append('UMA')
            if self.Ley_27426_rezago:
                datos_2.append(round(ultimos_valores[5] - ultimos_valores[4],2))
                etiquetas_2.append('Ley 27426 con rezago')
            if self.Caliva_mas_anses:
                datos_2.append(round(ultimos_valores[6] - ultimos_valores[4],2))
                etiquetas_2.append('Caliva mas Anses')
            grafico2 = crear_graficos(datos_2, etiquetas_2)
        else:
            grafico2 = None
            
        return lista_filas, grafico1, grafico2, diccionario_comparacion
        
    def generar_pdf(self):
        lista_filas, grafico1, grafico2, diccionario_comparacion = self.obtener_datos()
        rendered = render_template(
            'calculadora_movilidad/resultado_calculadora_movilidad.html',
            filas=lista_filas, 
            comparacion=diccionario_comparacion, 
            grafico1 = grafico1,
            grafico2 = grafico2,
            monto = formatear_dinero(self.monto),
            datos_del_actor = self.datos_del_actor,
            expediente = self.expediente,
            beneficio = self.beneficio,
            fecha_inicio = transformar_fecha(self.fecha_inicio),
            fecha_adquisicion_del_derecho = self.fecha_adquisicion_del_derecho,
            ipc = self.ipc,
            uma = self.uma,
            ripte = self.ripte,
            movilidad_sentencia = self.movilidad_sentencia,
            Ley_27426_rezago = self.Ley_27426_rezago,
            Caliva_mas_anses = self.Caliva_mas_anses,
            comparacion_mov_sentencia_si = self.comparacion_mov_sentencia_si
        )
        # Crear el PDF en memoria
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)

        if pisa_status.err:
            # Manejar el error en caso de que la creación del PDF falle
            return "Error al crear el PDF", 500

        pdf_buffer.seek(0)

        # Enviar el PDF como respuesta
        return send_file(pdf_buffer, as_attachment=True, download_name='resultado.pdf', mimetype='application/pdf')