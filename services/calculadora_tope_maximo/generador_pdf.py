from xhtml2pdf import pisa
from io import BytesIO
from models.database import engine
from services.calculos import formatear_dinero, transformar_fecha
from flask import render_template
from datetime import datetime
from sqlalchemy import text
import plotly.graph_objects as go
import io
import base64
from decimal import Decimal


def transformar_fecha_2(fecha):
    """
    Transforma un objeto datetime.date a un formato 'MM/YYYY'.

    Args:
    - fecha (datetime.date): Fecha en formato datetime.date.

    Returns:
    - str: Fecha transformada en formato 'MM/YYYY'.
    """
    return fecha.strftime('%m/%Y')  # '%m/%Y' devuelve 'mes/año' en formato numérico

def obtener_monto(fecha_ingresada):
    # Convertir la fecha ingresada por el usuario a un objeto datetime.date
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM topes_maximo"))

        # Variables para almacenar la fila más cercana
        fila_cercana = None
        fecha_cercana = None

        for row in result:
            fila_dict = dict(zip(result.keys(), row))  # Convertir la fila en un diccionario
            fecha_fila = fila_dict['fecha']  # Asumiendo que la columna de la fecha se llama 'fecha'

            if fecha_fila <= fecha_ingresada_dt:
                # Comparar para encontrar la fecha más cercana
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = fila_dict

        if fila_cercana:
            # Extraer los valores usando los nombres de las columnas
            caliva_anses = fila_cercana['Caliva_Anses']
            anses = fila_cercana['anses']
            badaro = fila_cercana['badaro']
            badaro_cm = fila_cercana['badaro c+m']
            ocheintados_rem_max = fila_cercana['82% rem.max']
            rem_max = fila_cercana['remuneracion maxima']
            rem_max_imponible_cm_extendido_27551 = fila_cercana['rem max imponible c+m extendido 27551']
            anses_palavecino= fila_cercana['anses_palavecino']
            caliva_palavecino= fila_cercana['caliva_palavecino']
            badaro_cm_palavecino= fila_cercana['badaro_cm_palavecino']
            martinez = fila_cercana['martinez']
            RM_Badaro_FP_CM_P_Anses= fila_cercana['RM_Badaro_FP_CM_P_Anses']
            Alanis_Colina= fila_cercana['Alanis_Colina']





            return caliva_anses, anses, badaro, badaro_cm, ocheintados_rem_max, rem_max, rem_max_imponible_cm_extendido_27551, martinez, anses_palavecino, caliva_palavecino, badaro_cm_palavecino, RM_Badaro_FP_CM_P_Anses, Alanis_Colina
        else:
            return None

def obtener_datos_para_grafico(fecha_ingresada):
    # Convertir la fecha ingresada a un objeto datetime.date
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

    vector_resultado = []  # Lista para almacenar las tuplas con los datos

    with engine.connect() as conn:
        query = text("""
            SELECT fecha, Caliva_Anses, anses, badaro, `badaro c+m`, 
                   `82% rem.max`, `remuneracion maxima`, 
                   `rem max imponible c+m extendido 27551`, martinez, anses_palavecino, caliva_palavecino, badaro_cm_palavecino, RM_Badaro_FP_CM_P_Anses, Alanis_Colina
            FROM topes_maximo
            WHERE fecha <= :fecha_ingresada
            ORDER BY fecha ASC
        """)

        # Usar .mappings() para obtener un resultado como diccionario
        result = conn.execute(query, {"fecha_ingresada": fecha_ingresada_dt}).mappings().all()

        # Recorrer el resultado y guardar los datos en tuplas
        for row in result:
            fila = (
                row['fecha'],
                row['anses'],
                row['Caliva_Anses'],
                row['badaro'],
                row['badaro c+m'],
                row['82% rem.max'],
                row['remuneracion maxima'],
                row['rem max imponible c+m extendido 27551'],
                row['martinez'],
                row['anses_palavecino'],
                row['caliva_palavecino'],
                row['badaro_cm_palavecino'],
                row['RM_Badaro_FP_CM_P_Anses'],
                row['Alanis_Colina'],


            )
            vector_resultado.append(fila)

    return vector_resultado
    
def crear_grafico_tope_haber_maximo(datos, nombre_grafico, etiquetas):
    etiquetas = etiquetas
    valores = datos

    # Verificar si la lista de valores está vacía
    if not valores:
        return "No hay datos suficientes para generar el gráfico."

    resultados = list(map(formatear_dinero, valores))

    # Encontrar el valor menor de los valores
    valor_minimo = min(valores)

    # Crear el gráfico
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
        marker_color=['#38225b', '#18488a', '#006faf', '#0096c6', '#7E7F9C', '#00bccb', '#00e0c4'],
        text=resultados, textposition='auto',
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
        xaxis_title='', 
        yaxis_title='',
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


def generar_grafico_linea(lista_filas, anses, caliva_anses, badaro, badaro_cm, ochenta_dos_rem_max, 
                          rem_max, rem_max_imponible_cm_extendido_27551, martinez, anses_palavecino, caliva_palavecino, badaro_cm_palavecino, RM_Badaro_FP_CM_P_Anses, Alanis_Colina, titulo):
    """
    Genera un gráfico de líneas en formato Base64 usando Plotly a partir de los datos proporcionados.

    Args:
    - lista_filas (list): Lista de tuplas donde cada tupla representa una fila (fecha y montos).
    - anses, caliva_anses, ... (bool): Indicadores de inclusión de cada concepto en el gráfico.
    - titulo (str): Título del gráfico.

    Returns:
    - str: Imagen del gráfico codificada en Base64.
    """
    fechas = [transformar_fecha_2(fila[0]) for fila in lista_filas]
    montos_por_concepto = list(zip(*[fila[1:] for fila in lista_filas]))  # Extraer montos desde el segundo elemento

    # Nombres de los conceptos a graficar
    conceptos = ['ANSES', 'Caliva ANSES', 'Badaro', 'Badaro C+M', '82% Rem Max', 
                 'Remuneración Máxima', 'Rem Max Imponible C+M Extendido 27551', 'Martínez', 'Anses Palavecino', 'Caliva Palavecino', 'Badaro C+M Palavecino', 'RM+Badaro+FP+CM+P+Anses', 'Alanis Colina']

    # Lista de booleanos correspondientes a los conceptos
    booleanos = [anses, caliva_anses, badaro, badaro_cm, ochenta_dos_rem_max, 
                 rem_max, rem_max_imponible_cm_extendido_27551, martinez, anses_palavecino, caliva_palavecino, badaro_cm_palavecino, RM_Badaro_FP_CM_P_Anses, Alanis_Colina]

    # Crear la figura con las líneas correspondientes
    fig = go.Figure()

    for i, (monto, incluir) in enumerate(zip(montos_por_concepto, booleanos)):
        if incluir:  # Solo agregar la línea si el booleano es True
            fig.add_trace(go.Scatter(
                x=fechas,
                y=[float(m) for m in monto],  # Convertir los montos a float
                mode='lines',
                name=conceptos[i]
            ))

    # Configurar el layout del gráfico
    fig.update_layout(
        title=titulo,
        xaxis_title='Fecha',
        yaxis_title='Monto ($)',
        legend_title='Conceptos',
        xaxis=dict(type='category'),
        yaxis=dict(tickformat=',', title='Monto ($)'),  # Formato con separadores de miles
        template='plotly_white',
        plot_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del área de trazado transparente
        paper_bgcolor='rgba(0, 0, 0, 0)'  # Fondo del gráfico transparente
    )

    # Crear un buffer en memoria y guardar la imagen en formato PNG
    buffer = io.BytesIO()
    fig.write_image(buffer, format='png')
    buffer.seek(0)

    # Codificar la imagen en Base64
    imagen_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    buffer.close()

    return imagen_base64

class Comparativa:
  def __init__(self, autos, expediente, periodo_hasta, haber_reclamado, caliva_mas_anses,badaro_mas_anses, badaro_mas_caliva, remuneracion_maxima, ochentaidos_remuneracion_maxima, rem_max_caliva_27551, martinez_mas_anses, anses_mas_palavecino, caliva_marquez_mas_palavecino, badaro_cm_palavecino, RM_Badaro_FP_CM_P_Anses, Alanis_Colina):
      self.autos = autos
      self.expediente = expediente
      self.periodo_hasta = periodo_hasta
      self.haber_reclamado = haber_reclamado
      self.caliva_mas_anses = caliva_mas_anses
      self.badaro_mas_anses = badaro_mas_anses
      self.badaro_mas_caliva = badaro_mas_caliva
      self.remuneracion_maxima = remuneracion_maxima
      self.ochenintados_remuneracion_maxima = ochentaidos_remuneracion_maxima
      self.rem_max_caliva_27551 = rem_max_caliva_27551
      self.martinez_mas_anses = martinez_mas_anses
      self.anses_mas_palavecino = anses_mas_palavecino
      self.caliva_marquez_mas_palavecino = caliva_marquez_mas_palavecino
      self.badaro_cm_palavecino = badaro_cm_palavecino
      self.RM_Badaro_FP_CM_P_Anses = RM_Badaro_FP_CM_P_Anses
      self.Alanis_Colina = Alanis_Colina
      
  def obtener_datos(self):

      caliva_anses, anses_2, badaro_2, badaro_cm_2, ocheintados_rem_max_2, rem_max_2,rem_max_imponible_cm_extendido_27551_2, martinez_2, anses_mas_palavecino_2, caliva_marquez_mas_palavecino_2, badaro_cm_palavecino_2, RM_Badaro_FP_CM_P_Anses, Alanis_Colina = obtener_monto(self.periodo_hasta)
      
      datos = {}
      
      datos['autos'] = self.autos
      datos['expediente'] = self.expediente
      datos['periodo_hasta'] = self.periodo_hasta
      datos['haber_reclamado'] = self.haber_reclamado

      datos['caliva_anses'] = caliva_anses
      datos['anses_2'] = anses_2
      datos['badaro_2'] = badaro_2
      datos['badaro_cm_2'] = badaro_cm_2
      datos['ocheintados_rem_max_2'] = ocheintados_rem_max_2
      datos['rem_max_2'] = rem_max_2
      datos['rem_max_imponible_cm_extendido_27551_2'] = rem_max_imponible_cm_extendido_27551_2
      datos['martinez_2'] = martinez_2
      datos['anses_mas_palavecino_2'] = anses_mas_palavecino_2
      datos['caliva_marquez_mas_palavecino_2'] = caliva_marquez_mas_palavecino_2
      datos['badaro_cm_palavecino_2'] = badaro_cm_palavecino_2
      datos['RM_Badaro_FP_CM_P_Anses'] = RM_Badaro_FP_CM_P_Anses
      datos['Alanis_Colina'] = Alanis_Colina


      datos['dif_caliva_anses']  = str(round((caliva_anses / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_caliva_anses']  = formatear_dinero(caliva_anses - anses_2)

      datos['dif_badaro_anses']  = str(round((badaro_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_badaro_anses']  = formatear_dinero(badaro_2 - anses_2)

      datos['dif_badaro_cm_anses']  = str(round((badaro_cm_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_badaro_cm_anses']  = formatear_dinero(badaro_cm_2 - anses_2)
      
      datos['dif_ocheintados_rem_max_anses']  = str(round((ocheintados_rem_max_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_ocheintados_rem_max_anses']  = formatear_dinero(ocheintados_rem_max_2 - anses_2)

      datos['dif_rem_max_anses']  = str(round((rem_max_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_rem_max_anses']  = formatear_dinero(rem_max_2 - anses_2)

      datos['dif_rem_max_imponible_cm_extendido_27551_anses']  = str(round((rem_max_imponible_cm_extendido_27551_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_rem_max_imponible_cm_extendido_27551_anses']  = formatear_dinero(rem_max_imponible_cm_extendido_27551_2 - anses_2)

      datos['dif_martinez_anses']  = str(round((martinez_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_martinez_anses']  = formatear_dinero(martinez_2 - anses_2)

      datos['dif_palavecino_anses']  = str(round((anses_mas_palavecino_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_palavecino_anses']  = formatear_dinero(anses_mas_palavecino_2 - anses_2)

      datos['dif_palavecino_caliva_anses']  = str(round((caliva_marquez_mas_palavecino_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_palavecino_caliva_anses']  = formatear_dinero(caliva_marquez_mas_palavecino_2 - anses_2)

      datos['dif_palavecino_badaro_cm_anses']  = str(round((badaro_cm_palavecino_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_palavecino_badaro_cm_anses']  = formatear_dinero(badaro_cm_palavecino_2 - anses_2)

      datos['dif_RM_Badaro_FP_CM_P_Anses_anses']  = str(round((RM_Badaro_FP_CM_P_Anses / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_RM_Badaro_FP_CM_P_Anses_anses']  = formatear_dinero(RM_Badaro_FP_CM_P_Anses - anses_2)

      datos['dif_Alanis_Colina_anses']  = str(round((Alanis_Colina / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_Alanis_Colina_anses']  = formatear_dinero(Alanis_Colina - anses_2)

      
      
      datos['dif_haber_reclamado_anses'] = formatear_dinero(Decimal(self.haber_reclamado) - anses_2)
      datos['dif_haber_reclamado_anses_graf'] = (Decimal(self.haber_reclamado) - anses_2)
      datos['porc_haber_reclamado_anses'] = str(round((Decimal(self.haber_reclamado) / anses_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_Caliva'] = formatear_dinero(Decimal(self.haber_reclamado) - caliva_anses)
      datos['dif_haber_reclamado_Caliva_graf'] = (Decimal(self.haber_reclamado) - caliva_anses)
      datos['porc_haber_reclamado_Caliva'] = str(round((Decimal(self.haber_reclamado) / caliva_anses - 1) * 100, 2)) + "%"
      
      datos['dif_haber_reclamado_Badaro'] = formatear_dinero(Decimal(self.haber_reclamado) - badaro_2)
      datos['dif_haber_reclamado_Badaro_graf'] = (Decimal(self.haber_reclamado) - badaro_2)
      datos['porc_haber_reclamado_Badaro'] = str(round((Decimal(self.haber_reclamado) / badaro_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_Badaro_CM'] = formatear_dinero(Decimal(self.haber_reclamado) - badaro_cm_2)
      datos['dif_haber_reclamado_Badaro_CM_graf'] = (Decimal(self.haber_reclamado) - badaro_cm_2)
      datos['porc_haber_reclamado_Badaro_CM'] = str(round((Decimal(self.haber_reclamado) / badaro_cm_2 - 1) * 100, 2)) + "%"
      datos['dif_haber_reclamado_ocheintados_rem_max_2'] = formatear_dinero(Decimal(self.haber_reclamado) - ocheintados_rem_max_2)
      datos['dif_haber_reclamado_ocheintados_rem_max_2_graf'] = (Decimal(self.haber_reclamado) - ocheintados_rem_max_2)
      datos['porc_haber_reclamado_ocheintados_rem_max_2'] = str(round((Decimal(self.haber_reclamado) / ocheintados_rem_max_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_rem_max_2'] = formatear_dinero(Decimal(self.haber_reclamado) - rem_max_2)
      datos['dif_haber_reclamado_rem_max_2_graf'] = (Decimal(self.haber_reclamado) - rem_max_2)
      datos['porc_haber_reclamado_rem_max_2'] = str(round((Decimal(self.haber_reclamado) / rem_max_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'] = formatear_dinero(Decimal(self.haber_reclamado) - rem_max_imponible_cm_extendido_27551_2)
      datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf'] = (Decimal(self.haber_reclamado) - rem_max_imponible_cm_extendido_27551_2)
      datos['porc_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'] = str(round((Decimal(self.haber_reclamado) / rem_max_imponible_cm_extendido_27551_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_martinez_2'] = formatear_dinero(Decimal(self.haber_reclamado) - martinez_2)
      datos['dif_haber_reclamado_martinez_2_graf'] = (Decimal(self.haber_reclamado) - martinez_2)
      datos['porc_haber_reclamado_martinez_2'] = str(round((Decimal(self.haber_reclamado) / martinez_2 - 1) * 100, 2)) + "%"


      datos['dif_haber_reclamado_anses_mas_palavecino_2'] = formatear_dinero(Decimal(self.haber_reclamado) - anses_mas_palavecino_2)
      datos['dif_haber_reclamado_anses_mas_palavecino_2_graf'] = (Decimal(self.haber_reclamado) - anses_mas_palavecino_2)
      datos['porc_haber_reclamado_anses_mas_palavecino_2'] = str(round((Decimal(self.haber_reclamado) / anses_mas_palavecino_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_caliva_marquez_mas_palavecino_2'] = formatear_dinero(Decimal(self.haber_reclamado) - caliva_marquez_mas_palavecino_2)
      datos['dif_haber_reclamado_caliva_marquez_mas_palavecino_2_graf'] = (Decimal(self.haber_reclamado) - caliva_marquez_mas_palavecino_2)
      datos['porc_haber_reclamado_caliva_marquez_mas_palavecino_2'] = str(round((Decimal(self.haber_reclamado) / caliva_marquez_mas_palavecino_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_badaro_cm_palavecino_2'] = formatear_dinero(Decimal(self.haber_reclamado) - badaro_cm_palavecino_2)
      datos['dif_haber_reclamado_badaro_cm_palavecino_2_graf'] = (Decimal(self.haber_reclamado) - badaro_cm_palavecino_2)
      datos['porc_haber_reclamado_badaro_cm_palavecino_2'] = str(round((Decimal(self.haber_reclamado) / badaro_cm_palavecino_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_RM_Badaro_FP_CM_P_Anses'] = formatear_dinero(Decimal(self.haber_reclamado) - RM_Badaro_FP_CM_P_Anses)
      datos['dif_haber_reclamado_RM_Badaro_FP_CM_P_Anses_graf'] = (Decimal(self.haber_reclamado) - RM_Badaro_FP_CM_P_Anses)
      datos['porc_haber_reclamado_RM_Badaro_FP_CM_P_Anses'] = str(round((Decimal(self.haber_reclamado) / RM_Badaro_FP_CM_P_Anses - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_Alanis_Colina'] = formatear_dinero(Decimal(self.haber_reclamado) - Alanis_Colina)
      datos['dif_haber_reclamado_Alanis_Colina_graf'] = (Decimal(self.haber_reclamado) - Alanis_Colina)
      datos['porc_haber_reclamado_Alanis_Colina'] = str(round((Decimal(self.haber_reclamado) / Alanis_Colina - 1) * 100, 2)) + "%"


      return datos

  def generar_pdf(self):
      vector_grafico = obtener_datos_para_grafico(self.periodo_hasta)
      grafico_3 = generar_grafico_linea(vector_grafico, True, self.caliva_mas_anses, self.badaro_mas_anses, self.badaro_mas_caliva, self.ochenintados_remuneracion_maxima,self.remuneracion_maxima,self.rem_max_caliva_27551,self.martinez_mas_anses, self.anses_mas_palavecino, self.caliva_marquez_mas_palavecino, self.badaro_cm_palavecino, self.RM_Badaro_FP_CM_P_Anses, self.Alanis_Colina, ("Evolucion de los Topes a lo largo del periodo"))
      
      datos = self.obtener_datos()
      datos_grafico = []
      etiquetas = []
      datos_grafico.append(datos['anses_2'])
      etiquetas.append('Tope Anses')
      if self.caliva_mas_anses:
          datos_grafico.append(datos['caliva_anses'])
          etiquetas.append('Tope Caliva Marquez mas Anses')
      if self.badaro_mas_anses:
          datos_grafico.append(datos['badaro_2'])
          etiquetas.append('Tope Badaro mas Anses')
      if self.badaro_mas_caliva:
          datos_grafico.append(datos['badaro_cm_2'])
          etiquetas.append('Tope Badaro mas Caliva Marquez')
      if self.ochenintados_remuneracion_maxima:
          datos_grafico.append(datos['ocheintados_rem_max_2'])
          etiquetas.append('82% de la Rem Max')
      if self.remuneracion_maxima:
          datos_grafico.append(datos['rem_max_2'])
          etiquetas.append('Rem. Maxima')
      if self.rem_max_caliva_27551:
          datos_grafico.append(datos['rem_max_imponible_cm_extendido_27551_2'])
          etiquetas.append('Rem Max Imponible C+M extendido 27551')
      if self.martinez_mas_anses:
          datos_grafico.append(datos['martinez_2'])
          etiquetas.append('Martinez mas Anses')
      if self.anses_mas_palavecino:
            datos_grafico.append(datos['anses_mas_palavecino_2'])
            etiquetas.append('Anses mas Palavecino')
      if self.caliva_marquez_mas_palavecino:
            datos_grafico.append(datos['caliva_marquez_mas_palavecino_2'])
            etiquetas.append('Caliva Marquez mas Palavecino')
      if self.badaro_cm_palavecino:
            datos_grafico.append(datos['badaro_cm_palavecino_2'])
            etiquetas.append('Badaro CM Palavecino')
      if self.RM_Badaro_FP_CM_P_Anses:
            datos_grafico.append(datos['RM_Badaro_FP_CM_P_Anses'])
            etiquetas.append('Tope RM+Badaro+FP+CM+P+Anses')

      if self.Alanis_Colina:
          datos_grafico.append(datos['Alanis_Colina'])
          etiquetas.append('Tope Alanis mas Colina')

      
      datos_grafico_2 = []
      etiquetas_2 = []
      datos_grafico_2.append(datos['dif_haber_reclamado_anses_graf'])
      etiquetas_2.append('Tope Anses')
      
      if self.caliva_mas_anses:
          datos_grafico_2.append(datos['dif_haber_reclamado_Caliva_graf'])
          etiquetas_2.append('Tope Caliva Marquez mas Anses')
      if self.badaro_mas_anses:
            datos_grafico_2.append(datos['dif_haber_reclamado_Badaro_graf'])
            etiquetas_2.append('Tope Badaro mas Anses')
      if self.badaro_mas_caliva:
             datos_grafico_2.append(datos['dif_haber_reclamado_Badaro_CM_graf'])
             etiquetas_2.append('Tope Badaro mas Caliva Marquez')
      if self.ochenintados_remuneracion_maxima:
            datos_grafico_2.append(datos['dif_haber_reclamado_ocheintados_rem_max_2_graf'])
            etiquetas_2.append('82% de la Rem Max')
      if self.remuneracion_maxima:
           datos_grafico_2.append(datos['dif_haber_reclamado_rem_max_2_graf'])
           etiquetas_2.append('Rem. Maxima')
      if self.rem_max_caliva_27551:
              datos_grafico_2.append(datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf'])
              etiquetas_2.append('Rem Max Imponible C+M extendido 27551')
      if self.martinez_mas_anses:
            datos_grafico_2.append(datos['dif_haber_reclamado_martinez_2_graf'])
            etiquetas_2.append('Martinez mas Anses')
      if self.anses_mas_palavecino:
          datos_grafico_2.append(datos['dif_haber_reclamado_anses_mas_palavecino_2_graf'])
          etiquetas_2.append('Anses mas Palavecino')
      if self.caliva_marquez_mas_palavecino:
          datos_grafico_2.append(datos['dif_haber_reclamado_caliva_marquez_mas_palavecino_2_graf'])
          etiquetas_2.append('Caliva Marquez mas Palavecino')
      if self.badaro_cm_palavecino:
          datos_grafico_2.append(datos['dif_haber_reclamado_badaro_cm_palavecino_2_graf'])
          etiquetas_2.append('Badaro CM Palavecino')
      if self.RM_Badaro_FP_CM_P_Anses:
            datos_grafico_2.append(datos['dif_haber_reclamado_RM_Badaro_FP_CM_P_Anses_graf'])
            etiquetas_2.append('Tope RM+Badaro+FP+CM+P+Anses')

      if self.Alanis_Colina:
          datos_grafico_2.append(datos['dif_haber_reclamado_Alanis_Colina_graf'])
          etiquetas_2.append('Tope Alanis mas Colina')
          
      grafico = crear_grafico_tope_haber_maximo(datos_grafico, "Diferencia en $ entre Topes", etiquetas)
      grafico_2 = crear_grafico_tope_haber_maximo(datos_grafico_2, "Diferencias en $ aplicando los Topes", etiquetas_2)

      rendered = render_template(
          'calculadora_tope_maximo/resultado.html',
          autos=self.autos,
          expediente=self.expediente,
          periodo_hasta=transformar_fecha(self.periodo_hasta),
          haber_reclamado = formatear_dinero(self.haber_reclamado),
          caliva_mas_anses = self.caliva_mas_anses,  
          badaro_mas_anses = self.badaro_mas_anses,  
          badaro_mas_caliva = self.badaro_mas_caliva,  
          remuneracion_maxima = self.remuneracion_maxima,  
          ochentaidos_remuneracion_maxima = self.ochenintados_remuneracion_maxima,  
          rem_max_caliva_27551 = self.rem_max_caliva_27551,  
          martinez_mas_anses = self.martinez_mas_anses,
          anses_mas_palavecino = self.anses_mas_palavecino,
          caliva_marquez_mas_palavecino = self.caliva_marquez_mas_palavecino,
          badaro_cm_palavecino = self.badaro_cm_palavecino,
          RM_Badaro_FP_CM_P_Anses = self.RM_Badaro_FP_CM_P_Anses,
          
          caliva_anses=formatear_dinero(datos['caliva_anses']),
          anses_2=formatear_dinero(datos['anses_2']),
          badaro_2=formatear_dinero(datos['badaro_2']),
          badaro_cm_2=formatear_dinero(datos['badaro_cm_2']),
          ocheintados_rem_max_2=formatear_dinero(datos['ocheintados_rem_max_2']),
          rem_max_2=formatear_dinero(datos['rem_max_2']),
          rem_max_imponible_cm_extendido_27551_2=formatear_dinero(datos['rem_max_imponible_cm_extendido_27551_2']),
          martinez_2=formatear_dinero(datos['martinez_2']),
          anses_mas_palavecino_2=formatear_dinero(datos['anses_mas_palavecino_2']),
          caliva_marquez_mas_palavecino_2=formatear_dinero(datos['caliva_marquez_mas_palavecino_2']),
          badaro_cm_palavecino_2=formatear_dinero(datos['badaro_cm_palavecino_2']),
          RM_Badaro_FP_CM_P_Anses_2=formatear_dinero(datos['RM_Badaro_FP_CM_P_Anses']),
          Alanis_Colina=formatear_dinero(datos['Alanis_Colina']),



          dif_caliva_anses=datos['dif_caliva_anses'],
          dif_monto_caliva_anses=datos['dif_monto_caliva_anses'] ,
          
          dif_badaro_anses=datos['dif_badaro_anses'],
          dif_monto_badaro_anses=datos['dif_monto_badaro_anses'],
          
          dif_badaro_cm_anses=datos['dif_badaro_cm_anses'],
          dif_monto_badaro_cm_anses=datos['dif_monto_badaro_cm_anses'],
          
          dif_ocheintados_rem_max_anses=datos['dif_ocheintados_rem_max_anses'],
          dif_monto_ocheintados_rem_max_anses=datos['dif_monto_ocheintados_rem_max_anses'],
          
          dif_rem_max_anses=datos['dif_rem_max_anses'],
          dif_monto_rem_max_anses=datos['dif_monto_rem_max_anses'],
          
          dif_rem_max_imponible_cm_extendido_27551_anses= datos['dif_rem_max_imponible_cm_extendido_27551_anses'],
          dif_monto_rem_max_imponible_cm_extendido_27551_anses= datos['dif_monto_rem_max_imponible_cm_extendido_27551_anses'],

          dif_martinez_anses=datos['dif_martinez_anses'],
          dif_monto_martinez_anses=datos['dif_monto_martinez_anses'],

          dif_anses_palavecino=datos['dif_palavecino_anses'],
          dif_monto_anses_palavecino=datos['dif_monto_palavecino_anses'],

          dif_caliva_palavecino=datos['dif_palavecino_caliva_anses'],
          dif_monto_caliva_palavecino=datos['dif_monto_palavecino_caliva_anses'],

          dif_badaro_cm_palavecino=datos['dif_palavecino_badaro_cm_anses'],
          dif_monto_badaro_cm_palavecino=datos['dif_monto_palavecino_badaro_cm_anses'],

          dif_RM_Badaro_FP_CM_P_Anses=datos['dif_RM_Badaro_FP_CM_P_Anses_anses'],
          dif_monto_RM_Badaro_FP_CM_P_Anses=datos['dif_monto_RM_Badaro_FP_CM_P_Anses_anses'],

          dif_Alanis_Colina=datos['dif_Alanis_Colina_anses'],
          dif_monto_Alanis_Colina=datos['dif_monto_Alanis_Colina_anses'],

          
          
          dif_haber_reclamado_anses = datos['dif_haber_reclamado_anses'],
          porc_haber_reclamado_anses = datos['porc_haber_reclamado_anses'],
          
          dif_haber_reclamado_Caliva = datos['dif_haber_reclamado_Caliva'],
          porc_haber_reclamado_Caliva = datos['porc_haber_reclamado_Caliva'],

          dif_haber_reclamado_Badaro = datos['dif_haber_reclamado_Badaro'],
          porc_haber_reclamado_Badaro = datos['porc_haber_reclamado_Badaro'],

          dif_haber_reclamado_Badaro_CM = datos['dif_haber_reclamado_Badaro_CM'],
          porc_haber_reclamado_Badaro_CM = datos['porc_haber_reclamado_Badaro_CM'],

          dif_haber_reclamado_ocheintados_rem_max_2= datos['dif_haber_reclamado_ocheintados_rem_max_2'],
          porc_haber_reclamado_ocheintados_rem_max_2 = datos['porc_haber_reclamado_ocheintados_rem_max_2'],

          dif_haber_reclamado_rem_max_2= datos['dif_haber_reclamado_rem_max_2'],
          porc_haber_reclamado_rem_max_2 = datos['porc_haber_reclamado_rem_max_2'],

          dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2 = datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'],
          porc_haber_reclamado_rem_max_imponible_cm_extendido_27551_2= datos['porc_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'],

          dif_haber_reclamado_martinez_2= datos['dif_haber_reclamado_martinez_2'],
          porc_haber_reclamado_martinez_2 = datos['porc_haber_reclamado_martinez_2'],

          dif_haber_reclamado_anses_mas_palavecino_2= datos['dif_haber_reclamado_anses_mas_palavecino_2'],
          porc_haber_reclamado_anses_mas_palavecino_2 = datos['porc_haber_reclamado_anses_mas_palavecino_2'],

          dif_haber_reclamado_caliva_marquez_mas_palavecino_2= datos['dif_haber_reclamado_caliva_marquez_mas_palavecino_2'],
          porc_haber_reclamado_caliva_marquez_mas_palavecino_2 = datos['porc_haber_reclamado_caliva_marquez_mas_palavecino_2'],

          dif_haber_reclamado_badaro_cm_palavecino_2= datos['dif_haber_reclamado_badaro_cm_palavecino_2'],
          porc_haber_reclamado_badaro_cm_palavecino_2 = datos['porc_haber_reclamado_badaro_cm_palavecino_2'],

          dif_haber_reclamado_RM_Badaro_FP_CM_P_Anses= datos['dif_haber_reclamado_RM_Badaro_FP_CM_P_Anses'],
          porc_haber_reclamado_RM_Badaro_FP_CM_P_Anses = datos['porc_haber_reclamado_RM_Badaro_FP_CM_P_Anses'],

          dif_haber_reclamado_Alanis_Colina= datos['dif_haber_reclamado_Alanis_Colina'],
          porc_haber_reclamado_Alanis_Colina = datos['porc_haber_reclamado_Alanis_Colina'],
      
          dif_haber_reclamado_anses_graf = datos['dif_haber_reclamado_anses_graf'],
          dif_haber_reclamado_Caliva_graf = datos['dif_haber_reclamado_Caliva_graf'],
          dif_haber_reclamado_Badaro_graf = datos['dif_haber_reclamado_Badaro_graf'],
          dif_haber_reclamado_Badaro_CM_graf = datos['dif_haber_reclamado_Badaro_CM_graf'],
          dif_haber_reclamado_ocheintados_rem_max_2_graf = datos['dif_haber_reclamado_ocheintados_rem_max_2_graf'],
          dif_haber_reclamado_rem_max_2_graf = datos['dif_haber_reclamado_rem_max_2_graf'],
          dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf = datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf'],
          dif_haber_reclamado_martinez_2_graf = datos['dif_haber_reclamado_martinez_2_graf'],
          dif_haber_reclamado_anses_mas_palavecino_2_graf = datos['dif_haber_reclamado_anses_mas_palavecino_2_graf'],
          dif_haber_reclamado_caliva_marquez_mas_palavecino_2_graf = datos['dif_haber_reclamado_caliva_marquez_mas_palavecino_2_graf'],
          dif_haber_reclamado_badaro_cm_palavecino_2_graf = datos['dif_haber_reclamado_badaro_cm_palavecino_2_graf'],
          dif_haber_reclamado_RM_Badaro_FP_CM_P_Anses_graf = datos['dif_haber_reclamado_RM_Badaro_FP_CM_P_Anses_graf'],
          dif_haber_reclamado_Alanis_Colina_graf = datos['dif_haber_reclamado_Alanis_Colina_graf'],

          
          grafico = grafico,
          grafico_2 = grafico_2,
          grafico_3 = grafico_3,
         
      )

      pdf_buffer = BytesIO()
      pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
      pdf_buffer.seek(0)
      return pdf_buffer.getvalue()
