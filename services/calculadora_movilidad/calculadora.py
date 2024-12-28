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
from datetime import datetime


def convertir_fecha_periodo(fecha):
    # Convertir la fecha si es una cadena
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d')  # Ajusta el formato a como esté tu fecha
    return fecha.strftime('%m/%Y')



def crear_graficos(datos, etiquetas):
    etiquetas = etiquetas
    valores = datos
    resultados = list(map(formatear_dinero, valores))

    # Crear el gráfico de barras
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
        marker_color=['#7671FA','#00c4ff', '#E5EAF3', '#07244C', '#178DAD', '#7E7F9C', '#9e73a3', '#3cd7c4', '#83007f','#bb73b3'],
        text=resultados, textposition='auto',
        textfont=dict(size=14)
    ))

    # Agregar la línea horizontal en el nivel de la primera columna
    valor_primera_columna = valores[0]
    fig.add_shape(
        type="line",
        x0=-0.5,  # Colocar la línea al inicio del gráfico
        x1=len(etiquetas) - 0.5,  # Colocar la línea hasta el final del gráfico
        y0=valor_primera_columna,
        y1=valor_primera_columna,
        line=dict(color="red", width=3, dash="solid")
    )

    # Actualizar el diseño del gráfico
    fig.update_layout(
        title='', 
        xaxis_title='', 
        yaxis_title='',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=40, r=40, t=40, b=40),
        width=800, height=600,
        xaxis=dict(title_font=dict(size=14), tickfont=dict(size=10)),
        yaxis=dict(title_font=dict(size=14), tickfont=dict(size=15))
    )

    # Guardar el gráfico como imagen en un buffer
    img_bytes = fig.to_image(format="png")  # Usar Kaleido para generar la imagen

    # Codificar la imagen en base64
    grafico_base64 = base64.b64encode(img_bytes).decode('utf-8')

    return grafico_base64

class CalculadorMovilidad:
    def __init__(self, datos_del_actor, expediente,cuil_expediente, beneficio, num_beneficio, fecha_inicio, fecha_fin, fecha_adquisicion_del_derecho, monto, ipc, ripte, uma, movilidad_sentencia, Ley_27426_rezago, caliva_mas_anses, Caliva_Marquez_con_27551_con_3_rezago,Caliva_Marquez_con_27551_con_6_rezago,Alanis_Mas_Anses,Alanis_con_27551_con_3_meses_rezago, comparacion_mov_sentencia_si, comparacion_mov_sentencia_no, comparacion_mov_caliva, comparacion_mov_alanis ):
        self.datos_del_actor = datos_del_actor
        self.expediente = expediente
        self.cuil_expediente = cuil_expediente
        self.beneficio = beneficio
        self.num_beneficio = num_beneficio
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.fecha_adquisicion_del_derecho = fecha_adquisicion_del_derecho
        self.monto = monto
        self.ipc = ipc
        self.ripte = ripte
        self.uma = uma
        self.movilidad_sentencia = movilidad_sentencia
        self.Ley_27426_rezago = Ley_27426_rezago
        self.caliva_mas_anses = caliva_mas_anses
        self.Caliva_Marquez_con_27551_con_3_rezago = Caliva_Marquez_con_27551_con_3_rezago
        self.Caliva_Marquez_con_27551_con_6_rezago = Caliva_Marquez_con_27551_con_6_rezago
        self.Alanis_Mas_Anses = Alanis_Mas_Anses
        self.Alanis_con_27551_con_3_meses_rezago = Alanis_con_27551_con_3_meses_rezago
        self.comparacion_mov_sentencia_si = comparacion_mov_sentencia_si
        self.comparacion_mov_sentencia_no = comparacion_mov_sentencia_no
        self.comparacion_mov_caliva = comparacion_mov_caliva
        self.comparacion_mov_alanis = comparacion_mov_alanis

    def obtener_datos(self):
        lista_filas, lista_montos = buscar_fechas(self.fecha_inicio,self.fecha_fin, self.monto)
        ultimos_valores = lista_montos[-1]
        diccionario_comparacion = {
               'dif_anses_ipc': formatear_dinero(ultimos_valores[1] - ultimos_valores[0]),
               'conf_anses_ipc': str(round((ultimos_valores[1] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_ipc': formatear_dinero(ultimos_valores[1] - ultimos_valores[4]),
               'conf_sent_ipc': str(round((ultimos_valores[1] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
            
               'dif_caliva_ipc': formatear_dinero(ultimos_valores[1] - ultimos_valores[7]),
               'conf_caliva_ipc': str(round((ultimos_valores[1] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_ipc': formatear_dinero(ultimos_valores[1] - ultimos_valores[9]),
               'conf_alanis_ipc': str(round((ultimos_valores[1] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
               #
               'dif_anses_ripte': formatear_dinero(ultimos_valores[2] - ultimos_valores[0]),
               'conf_anses_ripte': str(round((ultimos_valores[2] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_ripte': formatear_dinero(ultimos_valores[2] - ultimos_valores[4]),
               'conf_sent_ripte': str(round((ultimos_valores[2] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
               'dif_caliva_ripte': formatear_dinero(ultimos_valores[2] - ultimos_valores[7]),
               'conf_caliva_ripte': str(round((ultimos_valores[2] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_ripte': formatear_dinero(ultimos_valores[2] - ultimos_valores[9]),
               'conf_alanis_ripte': str(round((ultimos_valores[2] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
                #
               'dif_anses_UMA': formatear_dinero(ultimos_valores[3] - ultimos_valores[0]),
               'conf_anses_UMA': str(round((ultimos_valores[3] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_UMA': formatear_dinero(ultimos_valores[3] - ultimos_valores[4]),
               'conf_sent_UMA': str(round((ultimos_valores[3] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
               'dif_caliva_UMA': formatear_dinero(ultimos_valores[3] - ultimos_valores[7]),
               'conf_caliva_UMA': str(round((ultimos_valores[3] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_UMA': formatear_dinero(ultimos_valores[3] - ultimos_valores[9]),
               'conf_alanis_UMA': str(round((ultimos_valores[3] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
                #
               'dif_anses_sent': formatear_dinero(ultimos_valores[4] - ultimos_valores[0]),
               'conf_anses_sent': str(round((ultimos_valores[4] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",    
                #
               'dif_anses_ley27426': formatear_dinero(ultimos_valores[5] - ultimos_valores[0]),
               'conf_anses_ley27426': str(round((ultimos_valores[5] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
               'dif_sent_ley27426': formatear_dinero(ultimos_valores[5] - ultimos_valores[4]),
               'conf_sent_ley27426': str(round((ultimos_valores[5] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",           'dif_caliva_ley27426': formatear_dinero(ultimos_valores[5] - ultimos_valores[7]),
               'conf_caliva_ley27426': str(round((ultimos_valores[5] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_ley27426': formatear_dinero(ultimos_valores[5] - ultimos_valores[9]),
               'conf_alanis_ley27426': str(round((ultimos_valores[5] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
                #
                'dif_anses_Caliva_Marquez_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[6] - ultimos_valores[0]),
                'conf_anses_Caliva_Marquez_con_27551_con_3_rezago': str(round((ultimos_valores[6] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
                'dif_sent_Caliva_Marquez_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[6] - ultimos_valores[4]),
                'conf_sent_Caliva_Marquez_con_27551_con_3_rezago': str(round((ultimos_valores[6] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
                'dif_caliva_Caliva_Marquez_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[6] - ultimos_valores[7]),
                'conf_caliva_Caliva_Marquez_con_27551_con_3_rezago': str(round((ultimos_valores[6] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
                'dif_alanis_Caliva_Marquez_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[6] - ultimos_valores[9]),
                'conf_alanis_Caliva_Marquez_con_27551_con_3_rezago': str(round((ultimos_valores[6] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
                #
                'dif_anses_caliva_mas_anses': formatear_dinero(ultimos_valores[7] - ultimos_valores[0]),
                'conf_anses_caliva_mas_anses': str(round((ultimos_valores[7] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
                'dif_sent_caliva_mas_anses': formatear_dinero(ultimos_valores[7] - ultimos_valores[4]),
                'conf_sent_caliva_mas_anses': str(round((ultimos_valores[7] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
                'dif_alanis_caliva_mas_anses': formatear_dinero(ultimos_valores[7] - ultimos_valores[9]),
                'conf_alanis_caliva_mas_anses': str(round((ultimos_valores[7] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
                #
                'dif_anses_Caliva_Marquez_con_27551_con_6_rezago': formatear_dinero(ultimos_valores[8] - ultimos_valores[0]),
                'conf_anses_Caliva_Marquez_con_27551_con_6_rezago': str(round((ultimos_valores[8] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
                'dif_sent_Caliva_Marquez_con_27551_con_6_rezago': formatear_dinero(ultimos_valores[8] - ultimos_valores[4]),
                'conf_sent_Caliva_Marquez_con_27551_con_6_rezago': str(round((ultimos_valores[8] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
                #
                'dif_anses_alanis_mas_anses': formatear_dinero(ultimos_valores[9] - ultimos_valores[0]),
                'conf_anses_alanis_mas_anses': str(round((ultimos_valores[9] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
                'dif_sent_alanis_mas_anses': formatear_dinero(ultimos_valores[9] - ultimos_valores[4]),
                'conf_sent_alanis_mas_anses': str(round((ultimos_valores[9] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",  
                #
                'dif_anses_Alanis_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[10] - ultimos_valores[0]),
                'conf_anses_Alanis_con_27551_con_3_rezago': str(round((ultimos_valores[10] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",
                'dif_sent_Alanis_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[10] - ultimos_valores[4]),
                'conf_sent_Alanis_con_27551_con_3_rezago': str(round((ultimos_valores[10] - ultimos_valores[4]) / ultimos_valores[4] * 100, 2)) + "%",
                'dif_caliva_Alanis_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[10] - ultimos_valores[7]),
                'conf_caliva_Alanis_con_27551_con_3_rezago': str(round((ultimos_valores[10] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
                'dif_alanis_Alanis_con_27551_con_3_rezago': formatear_dinero(ultimos_valores[10] - ultimos_valores[9]),
                'conf_alanis_Alanis_con_27551_con_3_rezago': str(round((ultimos_valores[10] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
                #
           }    
        datos = [ultimos_valores[0]]
        etiquetas = ['Anses']
        if self.ipc:
            datos.append(ultimos_valores[1])
            #datos.append(round(ultimos_valores[1] - ultimos_valores[0],2))
            etiquetas.append('IPC')
        if self.ripte:
            datos.append(ultimos_valores[2])
            #datos.append(round(ultimos_valores[2] - ultimos_valores[0],2))
            etiquetas.append('RIPTE')
        if self.uma:
            datos.append(ultimos_valores[3])
            #datos.append(round(ultimos_valores[3] - ultimos_valores[0],2))
            etiquetas.append('UMA')
        if self.movilidad_sentencia:
            datos.append(ultimos_valores[4])
            #datos.append(round(ultimos_valores[4] - ultimos_valores[0],2))
            etiquetas.append('Movilidad de Sentencia (Caliva)')
        if self.Ley_27426_rezago:
            datos.append(ultimos_valores[5])
            #datos.append(round(ultimos_valores[5] - ultimos_valores[0],2))
            etiquetas.append('Ley 27426 con rezago')
        if self.Caliva_Marquez_con_27551_con_3_rezago:
            datos.append(ultimos_valores[6])
            #datos.append(round(ultimos_valores[6] - ultimos_valores[0],2))
            etiquetas.append('Caliva Marquez + fallo Cendan')
        if self.caliva_mas_anses:
            datos.append(ultimos_valores[7])
            #datos.append(round(ultimos_valores[7] - ultimos_valores[0],2))
            etiquetas.append('Caliva mas Anses')
        if self.Caliva_Marquez_con_27551_con_6_rezago:
            datos.append(ultimos_valores[8])
            #datos.append(round(ultimos_valores[8] - ultimos_valores[0],2))
            etiquetas.append('Caliva Marquez con 27551 con 6 rezago')
        if self.Alanis_Mas_Anses:
            datos.append(ultimos_valores[9])
            #datos.append(round(ultimos_valores[9] - ultimos_valores[0],2))
            etiquetas.append('Alanis mas Anses')
        if self.Alanis_con_27551_con_3_meses_rezago:
            datos.append(ultimos_valores[10])
            #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
            etiquetas.append('Alanis con 27551 con 3 rezago')
        grafico1 = crear_graficos(datos,etiquetas)

        if self.comparacion_mov_caliva:
                datos_2 = [ultimos_valores[7]]
                etiquetas_2 = ['Movilidad de Sentencia (Caliva)']
                if self.ipc:
                    datos_2.append(ultimos_valores[1])
                    #datos_2.append(round(ultimos_valores[1] - ultimos_valores[4],2))
                    etiquetas_2.append('IPC')
                if self.ripte:
                    datos_2.append(ultimos_valores[2])
                    #datos_2.append(round(ultimos_valores[2] - ultimos_valores[4],2))
                    etiquetas_2.append('RIPTE')
                if self.uma:
                    datos_2.append(ultimos_valores[3])
                    #datos_2.append(round(ultimos_valores[3] - ultimos_valores[4],2))
                    etiquetas_2.append('UMA')
                if self.Ley_27426_rezago:
                    datos_2.append(ultimos_valores[5])
                    #datos_2.append(round(ultimos_valores[5] - ultimos_valores[4],2))
                    etiquetas_2.append('Ley 27426 con rezago')
                if self.Caliva_Marquez_con_27551_con_3_rezago:
                    datos_2.append(ultimos_valores[6])
                    #datos_2.append(round(ultimos_valores[6] - ultimos_valores[4],2))
                    etiquetas_2.append('Caliva Marquez + Cendan')
                if self.Caliva_Marquez_con_27551_con_6_rezago:
                    datos_2.append(ultimos_valores[8])
                    #datos_2.append(round(ultimos_valores[8] - ultimos_valores[4],2))
                    etiquetas_2.append('Caliva Marquez con 27551 con 6 rezago')
                if self.Alanis_Mas_Anses:
                    datos_2.append(ultimos_valores[9])
                    #datos_2.append(round(ultimos_valores[9] - ultimos_valores[4],2))
                    etiquetas_2.append('Alanis mas Anses')
                if self.Alanis_con_27551_con_3_meses_rezago:
                    datos_2.append(ultimos_valores[10])
                    #datos_2.append(round(ultimos_valores[10] - ultimos_valores[4],2))
                    etiquetas_2.append('Alanis con 27551 con 3 rezago')
                grafico2 = crear_graficos(datos_2, etiquetas_2)
        else:
            grafico2 = None
        if self.comparacion_mov_alanis:
                datos_3 = [ultimos_valores[9]]
                etiquetas_3 = ['Movilidad de Sentencia (Alanis)']
                if self.ipc:
                    datos_3.append(ultimos_valores[1])
                    #datos_2.append(round(ultimos_valores[1] - ultimos_valores[4],2))
                    etiquetas_3.append('IPC')
                if self.ripte:
                    datos_3.append(ultimos_valores[2])
                    #datos_2.append(round(ultimos_valores[2] - ultimos_valores[4],2))
                    etiquetas_3.append('RIPTE')
                if self.uma:
                    datos_3.append(ultimos_valores[3])
                    #datos_2.append(round(ultimos_valores[3] - ultimos_valores[4],2))
                    etiquetas_3.append('UMA')
                if self.Ley_27426_rezago:
                    datos_3.append(ultimos_valores[5])
                    #datos_2.append(round(ultimos_valores[5] - ultimos_valores[4],2))
                    etiquetas_3.append('Ley 27426 con rezago')
                if self.Caliva_Marquez_con_27551_con_3_rezago:
                    datos_3.append(ultimos_valores[6])
                    #datos_2.append(round(ultimos_valores[6] - ultimos_valores[4],2))
                    etiquetas_3.append('Caliva Marquez + Cendan')
                if self.Caliva_Marquez_con_27551_con_6_rezago:
                    datos_3.append(ultimos_valores[8])
                    #datos_2.append(round(ultimos_valores[8] - ultimos_valores[4],2))
                    etiquetas_3.append('Caliva Marquez con 27551 con 6 rezago')
                if self.caliva_mas_anses:
                    datos_3.append(ultimos_valores[7])
                    #datos_2.append(round(ultimos_valores[9] - ultimos_valores[4],2))
                    etiquetas_3.append('Caliva mas Anses')
                if self.Alanis_con_27551_con_3_meses_rezago:
                    datos_3.append(ultimos_valores[10])
                    #datos_2.append(round(ultimos_valores[10] - ultimos_valores[4],2))
                    etiquetas_3.append('Alanis con 27551 con 3 rezago')
                grafico3 = crear_graficos(datos_3, etiquetas_3)
        else:
            grafico3 = None

        return lista_filas, grafico1, grafico2, grafico3, diccionario_comparacion, ultimos_valores

    def generar_pdf(self):
        lista_filas, grafico1, grafico2,grafico3, diccionario_comparacion, montos_a_fecha_cierre = self.obtener_datos()
        rendered = render_template(
            'calculadora_movilidad/resultado_calculadora_movilidad.html',
            filas=lista_filas, 
            comparacion=diccionario_comparacion, 
            grafico1 = grafico1,
            grafico2 = grafico2,
            grafico3 = grafico3,
            monto = formatear_dinero(self.monto),
            datos_del_actor = self.datos_del_actor,
            expediente = self.expediente,
            cuil_expediente = self.cuil_expediente,
            beneficio = self.beneficio,
            num_beneficio = self.num_beneficio,
            fecha_inicio = convertir_fecha_periodo(self.fecha_inicio),
            fecha_fin = convertir_fecha_periodo(self.fecha_fin),
            fecha_adquisicion_del_derecho = self.fecha_adquisicion_del_derecho,
            ipc = self.ipc,
            uma = self.uma,
            ripte = self.ripte,
            movilidad_sentencia = self.movilidad_sentencia,
            Ley_27426_rezago = self.Ley_27426_rezago,
            caliva_mas_anses = self.caliva_mas_anses,
            Caliva_Marquez_con_27551_con_3_rezago= self.Caliva_Marquez_con_27551_con_3_rezago,
            Caliva_Marquez_con_27551_con_6_rezago = self.Caliva_Marquez_con_27551_con_6_rezago,
            Alanis_Mas_Anses = self.Alanis_Mas_Anses,
            Alanis_con_27551_con_3_meses_rezago = self.Alanis_con_27551_con_3_meses_rezago,
            comparacion_mov_sentencia_si = self.comparacion_mov_sentencia_si,
            comparacion_mov_caliva= self.comparacion_mov_caliva,
            comparacion_mov_alanis= self.comparacion_mov_alanis,
            valor_anses = formatear_dinero(montos_a_fecha_cierre[0]),
            valor_ipc = formatear_dinero(montos_a_fecha_cierre[1]),
            valor_ripte = formatear_dinero(montos_a_fecha_cierre[2]),
            valor_uma = formatear_dinero(montos_a_fecha_cierre[3]),
            valor_mov_sentencia = formatear_dinero(montos_a_fecha_cierre[4]),
            valor_Ley_27426_rezago = formatear_dinero(montos_a_fecha_cierre[5]),
            valor_Caliva_Marquez_con_27551_con_3_rezago = formatear_dinero(montos_a_fecha_cierre[6]),
            valor_Caliva_mas_Anses = formatear_dinero(montos_a_fecha_cierre[7]),
            valor_Caliva_Marquez_con_27551_con_6_rezago = formatear_dinero(montos_a_fecha_cierre[8]),
            valor_Alanis_mas_Anses = formatear_dinero(montos_a_fecha_cierre[9]),
            valor_Alanis_con_27551_con_3_rezago = formatear_dinero(montos_a_fecha_cierre[10])

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