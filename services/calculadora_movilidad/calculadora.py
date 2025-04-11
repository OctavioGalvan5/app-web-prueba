import plotly.graph_objects as go
import io
import base64
from services.calculos import formatear_dinero, transformar_fecha
from models.database import engine
from flask import render_template, send_file
from werkzeug.wrappers import response
from config import config
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine, MetaData, Table, select, extract, text
from decimal import Decimal

def convertir_fecha_periodo(fecha):
    # Convertir la fecha si es una cadena
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d')  # Ajusta el formato a como esté tu fecha
    return fecha.strftime('%m/%Y')


def funcion_movilidad_personalizada(fecha_inicial, columna, monto, fecha_final, tupla_reajuste):
    with engine.connect() as connection:
        # Cargar la tabla desde la base de datos
        metadata = MetaData()
        tabla = Table('indices_de_movilidad', metadata, autoload_with=engine)

        # Inicializar variables y convertir fechas a tipo date si son datetime
        fecha_actual = datetime.strptime(fecha_inicial, "%Y-%m-%d").date() if isinstance(fecha_inicial, str) else fecha_inicial.date() if isinstance(fecha_inicial, datetime) else fecha_inicial
        fecha_actual = fecha_actual + relativedelta(months=1)  # Sumar un mes
        fecha_final = datetime.strptime(fecha_final, "%Y-%m-%d").date() if isinstance(fecha_final, str) else fecha_final.date() if isinstance(fecha_final, datetime) else fecha_final
        fecha_final = fecha_final.date() if isinstance(fecha_final, datetime) else fecha_final
        resultados = []
        resultado_dinero=[]
        columna_actual = columna

        # Iterar hasta alcanzar la fecha final
        while fecha_actual <= fecha_final:
            # Seleccionar el valor de la columna para el año y mes actuales
            consulta = select(tabla.c[columna_actual]).where(
                extract('year', tabla.c.fechas) == fecha_actual.year,
                extract('month', tabla.c.fechas) == fecha_actual.month
            )
            resultado = connection.execute(consulta).fetchone()

            # Si no hay datos, salir del bucle
            if not resultado:
                break

            # Multiplicar el monto por el valor de la columna y actualizar el monto acumulado
            valor = resultado[0]
            if valor is not None:
                monto *= valor  # Actualiza el monto acumulado multiplicando por el índice actual

            # Verificar si la fecha es 2020-03-01 y agregar 1500 al monto si coincide
            if fecha_actual == datetime(2020, 3, 1).date() and columna_actual == 'Aumentos_Anses':
                monto += 1500

            # Almacenar la fecha y el monto en resultados
            resultados.append(monto)
            resultado_dinero.append(formatear_dinero(monto))

            # Verificar si el mes y año de fecha_actual coinciden con alguna fecha en la tupla para cambiar de columna
            for ajuste in tupla_reajuste:
                if ajuste[0] is not None:
                    fecha = ajuste[0] + relativedelta(months=1)  # Sumar un mes
                    if fecha_actual.year == fecha.year and fecha_actual.month == fecha.month:
                        columna_actual = ajuste[1]  # Cambiar a la columna de ajuste
                        break

            # Incrementar fecha_actual a la siguiente fecha en la tabla
            fecha_actual = siguiente_fecha(connection, tabla, fecha_actual)

            # Si no se encuentra una siguiente fecha, termina el bucle
            if fecha_actual is None:
                break
        return resultados, resultado_dinero


# Función para obtener la siguiente fecha en la tabla
def siguiente_fecha(connection, tabla, fecha_actual):
    consulta = select(tabla.c.fechas).where(tabla.c.fechas > fecha_actual).order_by(tabla.c.fechas.asc()).limit(1)
    resultado = connection.execute(consulta).fetchone()
    return resultado[0] if resultado else None

def procesar_tupla_reajuste(tupla, haber_reajustado, monto, fecha_inicio):
    # Verificar si fecha_inicio es una cadena y convertirla a datetime si es necesario
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')  # Ajusta el formato según corresponda
        except ValueError:
            raise ValueError("Formato de fecha inválido. Se esperaba 'YYYY-MM-DD'.")

    # Ahora puedes usar strftime sin problemas
    resultado = "Se parte de un Haber Percibido de {} Pesos del {} ".format(
        formatear_dinero(monto), 
        fecha_inicio.strftime('%d/%m/%Y')
    )

    bandera = 0
    if haber_reajustado:
        for elemento in tupla:
            # Verifica si el primer elemento no es nulo
            if elemento[0] is not None:
                monto_reajuste = elemento[1]
                fecha_reajuste = elemento[0]

                # Verificar si fecha_reajuste es una cadena y convertirla a datetime si es necesario
                if isinstance(fecha_reajuste, str):
                    try:
                        fecha_reajuste = datetime.strptime(fecha_reajuste, '%Y-%m-%d')  # Ajusta el formato según corresponda
                    except ValueError:
                        raise ValueError("Formato de fecha inválido. Se esperaba 'YYYY-MM-DD'.")

                if bandera == 0:
                    resultado += " que el " + fecha_reajuste.strftime('%d/%m/%Y') + " fué reajustado a " + formatear_dinero(monto_reajuste)
                    bandera = 1
                else:
                    resultado += " y luego el " + fecha_reajuste.strftime('%d/%m/%Y') + " fué reajustado a " + formatear_dinero(monto_reajuste)

    return resultado.strip()  # Elimina espacios al final
def procesar_tuplas(tuplas, movilidad_1):

    diccionario = {
        'Aumentos_Anses': 'Aumentos Generales de la ANSeS por movilidad',
        'Salarios_Nivel_General_INDEC': 'Salarios Nivel General INDEC',
        'Aumento_de_Marzo_2018_Ley_26417_14': 'Aumento de Marzo 2018 Ley 26417 14%',
        'Aumentos_fallo_Marquez_Raimundo_por_Ley_27551': 'Aumentos fallo Marquez, Raimundo por Ley 27551',
        'Aumentos_fallo_Alanis_Daniel_Ley_27551_35_55_2020' : 'Aumentos fallo Alanis, Daniel Ley 27551 35,55% para el año 2020',
        'RIPTE_Remuneracion_Imponible_Promedio_Trabajadores_Estables' : 'RIPTE (Remuneración Imponible Promedio de Trabajadores Estables)',
        'RIPTE_Trimestral_Retrasado_3_Meses' : 'RIPTE trimestral retrasado 3 meses',
        'RIPTE_Retrasado_2_Meses' : 'RIPTE retrasado 2 meses',
        'IPC_Retrasado_2_Meses' : 'IPC retrasado 2 meses',
        'IPC_Retrasado_3_Meses' : 'IPC retrasado 3 meses',
        'Ley_27551_50_IPC_50_RIPTE_Trimestral_Retrasado_3_Meses' : 'Ley 27551 (50 % IPC y 50% RIPTE Trimestral retrasado 3 meses)',
        'Sin_Movilidad' : 'Sin Movilidad',
        'Aumentos_Poder_Judicial_de_la_Nacion' : 'Aumentos Poder Judicial de la Nacion',
        'IPC_Precios_Consumidor' : 'Precios al Consumidor o Costo de Vida (I.P.C.)',
        'Salarios_Nivel_General_INDEC_Anual' : 'Salarios Nivel General INDEC Anual',
        'Ley_27426_IPC_RIPTE_Trimestral_Diferido_3M' : 'Ley 27426 - IPC y Ripte Trimestral Diferido 3 meses',
        'Aumentos_fallo_Martinez' : 'Aumentos Fallo Martinez para el año 2020',

    }
    resultado = diccionario[movilidad_1]

    for elemento in tuplas:
        # Verifica si el primer elemento no es nulo
        if elemento[0] is not None:
            # Obtiene el string del segundo elemento
            clave = elemento[1]
            fecha = elemento[0]
            if clave in diccionario:
                if resultado != "":
                    resultado += " hasta el " + fecha.strftime('%d/%m/%Y') + " y desde ahi " + diccionario[clave] 


    return resultado.strip()  # Elimina espacios al final

def buscar_fechas(fecha_inicio, fecha_fin, monto,tupla_reajuste,haber_reajustado, fallecido, fecha_fallecimiento):
    # Convertir las fechas ingresadas a objetos datetime.date en formato 'yyyy-mm-dd'
    fecha_ingresada_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    fecha_ingresada_dt = fecha_ingresada_dt + relativedelta(months=1)  # Sumar un mes
    fecha_obj = datetime.strptime(fecha_fallecimiento, "%Y-%m-%d")
    nueva_fecha = fecha_obj + relativedelta(months=1)
    fecha_fallecimiento = nueva_fecha.strftime("%Y-%m-%d")
    fecha_fallecimiento = datetime.strptime(fecha_fallecimiento, "%Y-%m-%d") 

    lista_filas = []
    lista_montos = []

    with engine.connect() as conn:
        # Buscar la fila con la fecha más cercana menor a la ingresada
        result = conn.execute(
            text("SELECT * FROM tabla_movilidades WHERE fechas <= :fecha ORDER BY fechas DESC LIMIT 1"),
            {"fecha": fecha_ingresada_dt}
        )

        fila_menor = result.fetchone()  # Obtener la fila con la fecha más cercana menor

        if fila_menor:
            columnas = result.keys()  # Obtener los nombres de las columnas
            fila_dict = dict(zip(columnas, fila_menor))  # Convertir la fila a diccionario

            # Acceder a las columnas por nombre y calcular los montos
            monto_columna2 = Decimal(monto) * Decimal(fila_dict['ANSES'])
            monto_columna3 = Decimal(fila_dict['IPC']) * Decimal(monto)
            monto_columna4 = Decimal(fila_dict['RIPTE']) * Decimal(monto)
            monto_columna5 = Decimal(fila_dict['UMA']) * Decimal(monto)
            monto_columna6 = Decimal(fila_dict['alanis_ipc']) * Decimal(monto)
            monto_columna7 = Decimal(fila_dict['Ley_27426_IPC_RIPTE_Trimestral_Diferido_3M']) * Decimal(monto)
            monto_columna8 = Decimal(fila_dict['Caliva_Marquez_con_27551_con_3_rezago']) * Decimal(monto)
            monto_columna9 = Decimal(fila_dict['Caliva_mas_Anses']) * Decimal(monto)
            monto_columna10 = Decimal(fila_dict['alanis_ripte']) * Decimal(monto)
            monto_columna11 = Decimal(fila_dict['Alanis_Mas_Anses']) * Decimal(monto)
            monto_columna12 = Decimal(fila_dict['Alanis_con_27551_con_3_meses_rezago']) * Decimal(monto)
            monto_columna13 = Decimal(fila_dict['martinez']) * Decimal(monto)
            monto_columna14 = Decimal(fila_dict['alanis_ipc']) * Decimal(monto)
            monto_columna15 = Decimal(fila_dict['alanis_ripte']) * Decimal(monto)



            # Agregar la primera tupla a la lista
            lista_filas.append((
                convertir_fecha_periodo(fila_dict['fechas']),
                formatear_dinero(monto_columna2),
                formatear_dinero(monto_columna3),
                formatear_dinero(monto_columna4),
                formatear_dinero(monto_columna5),
                formatear_dinero(monto_columna6),
                formatear_dinero(monto_columna7),
                formatear_dinero(monto_columna8),
                formatear_dinero(monto_columna9),
                formatear_dinero(monto_columna10),
                formatear_dinero(monto_columna11),
                formatear_dinero(monto_columna12),
                formatear_dinero(monto_columna13),
                formatear_dinero(monto_columna14),
                formatear_dinero(monto_columna15),



            ))
            lista_montos.append((monto_columna2, monto_columna3, monto_columna4, monto_columna5, monto_columna6, monto_columna7,
                                 monto_columna8, monto_columna9, monto_columna10, monto_columna11, monto_columna12, monto_columna13, monto_columna14, monto_columna15))
        else:
            print("No se encontró una fecha menor a la ingresada.")
            return []

        # Buscar todas las filas con fechas mayores a la ingresada
        result_mayores = conn.execute(
            text("SELECT * FROM tabla_movilidades WHERE fechas > :fecha ORDER BY fechas ASC"),
            {"fecha": fecha_ingresada_dt}
        )

        filas_mayores = result_mayores.fetchall()

        if filas_mayores:
            for fila in filas_mayores:
                fila_dict = dict(zip(result_mayores.keys(), fila))  # Convertir la fila a diccionario


                if fallecido is not False and fila_dict['fechas'].year == fecha_fallecimiento.year and fila_dict['fechas'].month == fecha_fallecimiento.month:
                    if fila_dict['id'] == 243:
                        monto_columna2 = (monto_columna2 * Decimal(fila_dict['ANSES']) + Decimal(1500)) * Decimal(0.7)
                    else:
                        monto_columna2 = (monto_columna2 * Decimal(fila_dict['ANSES'])) * Decimal(0.7)

                    monto_columna3 *= Decimal(fila_dict['IPC'])
                    monto_columna3 = monto_columna3 * Decimal(0.7)
                    monto_columna4 *= Decimal(fila_dict['RIPTE'])
                    monto_columna4 = monto_columna4 * Decimal(0.7)
                    monto_columna5 *= Decimal(fila_dict['UMA'])
                    monto_columna5 = monto_columna5 * Decimal(0.7)
                    monto_columna6 *= Decimal(fila_dict['alanis_ipc'])
                    monto_columna6 = monto_columna6 * Decimal(0.7)
                    monto_columna7 *= Decimal(fila_dict['Ley_27426_IPC_RIPTE_Trimestral_Diferido_3M'])
                    monto_columna7 = monto_columna7 * Decimal(0.7)
                    monto_columna8 *= Decimal(fila_dict['Caliva_Marquez_con_27551_con_3_rezago'])
                    monto_columna8 = monto_columna8 * Decimal(0.7)
                    monto_columna9 *= Decimal(fila_dict['Caliva_mas_Anses'])
                    monto_columna9 = monto_columna9 * Decimal(0.7)
                    monto_columna10 *= Decimal(fila_dict['alanis_ripte'])
                    monto_columna10 = monto_columna10 * Decimal(0.7)
                    monto_columna11 *= Decimal(fila_dict['Alanis_Mas_Anses'])
                    monto_columna11 = monto_columna11 * Decimal(0.7)
                    monto_columna12 *= Decimal(fila_dict['Alanis_con_27551_con_3_meses_rezago'])
                    monto_columna12 = monto_columna12 * Decimal(0.7)
                    monto_columna13 *= Decimal(fila_dict['martinez'])
                    monto_columna13 = monto_columna13 * Decimal(0.7)
                    monto_columna14 *= Decimal(fila_dict['alanis_ipc'])
                    monto_columna14 = monto_columna14 * Decimal(0.7)
                    monto_columna15 *= Decimal(fila_dict['alanis_ripte'])
                    monto_columna15 = monto_columna15 * Decimal(0.7)

                else:  
                    if fila_dict['id'] == 243:
                        monto_columna2 = monto_columna2 * Decimal(fila_dict['ANSES']) + Decimal(1500)
                    else:
                        monto_columna2 = monto_columna2 * Decimal(fila_dict['ANSES'])

                    if haber_reajustado:
                        for elemento in tupla_reajuste:
                            if elemento[0] is not None and fila_dict['fechas'].year == elemento[0].year and fila_dict['fechas'].month == elemento[0].month:
                                monto_columna2 = elemento[1]
                                break

                    monto_columna3 *= Decimal(fila_dict['IPC'])
                    monto_columna4 *= Decimal(fila_dict['RIPTE'])
                    monto_columna5 *= Decimal(fila_dict['UMA'])
                    monto_columna6 *= Decimal(fila_dict['alanis_ipc'])
                    monto_columna7 *= Decimal(fila_dict['Ley_27426_IPC_RIPTE_Trimestral_Diferido_3M'])
                    monto_columna8 *= Decimal(fila_dict['Caliva_Marquez_con_27551_con_3_rezago'])
                    monto_columna9 *= Decimal(fila_dict['Caliva_mas_Anses'])
                    monto_columna10 *= Decimal(fila_dict['alanis_ripte'])
                    monto_columna11 *= Decimal(fila_dict['Alanis_Mas_Anses'])
                    monto_columna12 *= Decimal(fila_dict['Alanis_con_27551_con_3_meses_rezago'])
                    monto_columna13 *= Decimal(fila_dict['martinez'])
                    monto_columna14 *= Decimal(fila_dict['alanis_ipc'])
                    monto_columna15 *= Decimal(fila_dict['alanis_ripte'])


                lista_filas.append((
                    convertir_fecha_periodo(fila_dict['fechas']),
                    formatear_dinero(monto_columna2),
                    formatear_dinero(monto_columna3),
                    formatear_dinero(monto_columna4),
                    formatear_dinero(monto_columna5),
                    formatear_dinero(monto_columna6),
                    formatear_dinero(monto_columna7),
                    formatear_dinero(monto_columna8),
                    formatear_dinero(monto_columna9),
                    formatear_dinero(monto_columna10),
                    formatear_dinero(monto_columna11),
                    formatear_dinero(monto_columna12),
                    formatear_dinero(monto_columna13),
                    formatear_dinero(monto_columna14),
                    formatear_dinero(monto_columna15)

                ))
                lista_montos.append((monto_columna2, monto_columna3, monto_columna4, monto_columna5, monto_columna6, monto_columna7,
                                     monto_columna8, monto_columna9, monto_columna10, monto_columna11, monto_columna12, monto_columna13, monto_columna14, monto_columna15))

                if fila_dict['fechas'].year == fecha_fin_dt.year and fila_dict['fechas'].month == fecha_fin_dt.month:
                    break
        else:
            print("No se encontraron filas con fechas mayores a la ingresada.")
            return []

    return lista_filas, lista_montos


def transformar_fecha_2(fecha):
    """
    Transforma una fecha en formato 'YYYY-MM-DD' o 'MM/YYYY' (string) a formato 'MM/YYYY'.

    Args:
    - fecha (str): Fecha en formato 'YYYY-MM-DD' o 'MM/YYYY'.

    Returns:
    - str: Fecha transformada en formato 'MM/YYYY'.
    """
    # Verifica si la fecha está en el formato 'YYYY-MM-DD'
    try:
        # Si la fecha está en formato 'YYYY-MM-DD'
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    except ValueError:
        try:
            # Si la fecha está en formato 'MM/YYYY'
            fecha_obj = datetime.strptime(fecha, '%m/%Y')
        except ValueError:
            raise ValueError(f"Formato de fecha no válido: {fecha}")

    # Devolver la fecha en formato 'MM/YYYY'
    return fecha_obj.strftime('%m/%Y')


def convertir_fecha_periodo(fecha):
    # Convertir la fecha si es una cadena
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d')  # Ajusta el formato a como esté tu fecha
    return fecha.strftime('%m/%Y')


def generar_grafico_linea(lista_filas, ipc, ripte, uma, movilidad_sentencia, ley_27426_rezago, 
                          caliva_mas_anses, caliva_marquez_con_27551_con_3_rezago, 
                          caliva_marquez_con_27551_con_6_rezago, alanis_mas_anses, 
                          alanis_con_27551_con_3_meses_rezago, fallo_martinez, alanis_ipc, alanis_ripte, movilidad_personalizada, titulo, filas_dinero):


    lista_filas = [fila + (dinero,) for fila, dinero in zip(lista_filas, filas_dinero)]
    fechas = [transformar_fecha_2(fila[0]) for fila in lista_filas]  # Primer elemento de cada tupla (fecha)
    montos_por_concepto = list(zip(*[fila[1:] for fila in lista_filas]))  # Montos desde el segundo elemento en adelante

    # Nombres de los conceptos
    conceptos = ['ANSES', 'IPC', 'RIPTE', 'UMA', 'Mov de Sentencia', 'Ley 27426', 
                 'Caliva mas Cendan', 'Caliva mas Anses', 'Caliva 6 Rezago', 
                 'Alanis mas Anses', 'Alanis con 3 meses Rezago', 'Martínez', 'Alanis con IPC', 'Alanis con RIPTE', 'Movilidad Personalizada']

    # Lista de booleanos y sus correspondientes conceptos
    booleanos = [True, ipc, ripte, uma, movilidad_sentencia, ley_27426_rezago, 
                 caliva_marquez_con_27551_con_3_rezago, caliva_mas_anses, 
                 caliva_marquez_con_27551_con_6_rezago, alanis_mas_anses, 
                 alanis_con_27551_con_3_meses_rezago, fallo_martinez, alanis_ipc, alanis_ripte, movilidad_personalizada]

    # Crear una figura con una línea por cada concepto que tenga el booleano en True
    fig = go.Figure()

    for i, (monto, incluir) in enumerate(zip(montos_por_concepto, booleanos)):
        if incluir:  # Solo agregar la línea si el booleano es True
            fig.add_trace(go.Scatter(
                x=fechas,
                y=[float(m.replace('$', '').replace('.', '').replace(',', '.').replace(' ', '').strip()) for m in monto],
                mode='lines',
                name=conceptos[i]
            ))

    # Configurar el layout del gráfico
    fig.update_layout(
        title=('Acreditacion del Daño del haber de ' + titulo),
        xaxis_title='Fecha',
        yaxis_title='Monto ($)',
        legend_title='Conceptos',
        xaxis=dict(type='category'),
        yaxis=dict(tickformat=',', title='Monto ($)'),  # Formato con separadores de miles
        template='plotly_white',
        plot_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del área de trazado transparente
        paper_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del gráfico transparente
    )

    # Crear un buffer en memoria y guardar la imagen en formato PNG
    buffer = io.BytesIO()
    fig.write_image(buffer, format='png')
    buffer.seek(0)

    # Codificar la imagen en Base64
    imagen_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    buffer.close()

    return imagen_base64




def crear_graficos(datos, etiquetas, titulo):
    etiquetas = etiquetas
    valores = datos
    titulo = titulo
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

    # Actualizar el diseño del gráfico con título
    fig.update_layout(
        title=dict(
            text=titulo,  # Título del gráfico
            font=dict(size=20),  # Tamaño del título
            x=0,  # Alinea el título a la izquierda
            xanchor='left'  # Ancla el título a la izquierda
        ),
        xaxis_title='Categorías',  # Título del eje X
        yaxis_title='Monto ($)',  # Título del eje Y
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=40, r=40, t=60, b=40),
        width=800, height=600,
        xaxis=dict(title_font=dict(size=14), tickfont=dict(size=10)),
        yaxis=dict(title_font=dict(size=14), tickfont=dict(size=12))
    )

    # Guardar el gráfico como imagen en un buffer
    img_bytes = fig.to_image(format="png")  # Usar Kaleido para generar la imagen

    # Codificar la imagen en base64
    grafico_base64 = base64.b64encode(img_bytes).decode('utf-8')

    return grafico_base64

class CalculadorMovilidad:
    def __init__(self, datos_del_actor,fallecido, fecha_fallecimiento, cobrador_pension, expediente,cuil_expediente, beneficio, num_beneficio, fecha_inicio, fecha_fin, fecha_adquisicion_del_derecho, monto, ipc, ripte, uma, movilidad_sentencia, Ley_27426_rezago, caliva_mas_anses, Caliva_Marquez_con_27551_con_3_rezago,Caliva_Marquez_con_27551_con_6_rezago,Alanis_Mas_Anses,Alanis_con_27551_con_3_meses_rezago,fallo_martinez, alanis_ipc, alanis_ripte, comparacion_mov_sentencia_si, comparacion_mov_sentencia_no, comparacion_mov_caliva, comparacion_mov_alanis,movilidad_personalizada,movilidad_1, tupla, tupla_reajuste, haber_reajustado ):
        self.datos_del_actor = datos_del_actor
        self.fallecido = fallecido
        self.fecha_fallecimiento = fecha_fallecimiento
        self.cobrador_pension = cobrador_pension
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
        self.fallo_martinez = fallo_martinez
        self.alanis_ipc = alanis_ipc
        self.alanis_ripte = alanis_ripte
        self.comparacion_mov_sentencia_si = comparacion_mov_sentencia_si
        self.comparacion_mov_sentencia_no = comparacion_mov_sentencia_no
        self.comparacion_mov_caliva = comparacion_mov_caliva
        self.comparacion_mov_alanis = comparacion_mov_alanis
        self.movilidad_personalizada = movilidad_personalizada
        self.movilidad_1 = movilidad_1 
        self.tupla = tupla
        self.resultado = procesar_tuplas(self.tupla, self.movilidad_1)
        self.tupla_reajuste = tupla_reajuste
        self.haber_reajustado = haber_reajustado
        self.haber = procesar_tupla_reajuste(self.tupla_reajuste, self.haber_reajustado, self.monto, self.fecha_inicio)

    def obtener_datos(self):
        filas, filas_dinero = funcion_movilidad_personalizada(self.fecha_inicio, self.movilidad_1, self.monto, self.fecha_fin,self.tupla)
        ultimo_valor_personalizado = filas[-1]
        lista_filas, lista_montos = buscar_fechas(self.fecha_inicio,self.fecha_fin, self.monto, self.tupla_reajuste, self.haber_reajustado, self.fallecido, self.fecha_fallecimiento)
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
               'dif_anses_martinez': formatear_dinero(ultimos_valores[11] - ultimos_valores[0]),
               'conf_anses_martinez': str(round((ultimos_valores[11] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",

               'dif_caliva_martinez': formatear_dinero(ultimos_valores[11] - ultimos_valores[7]),
               'conf_caliva_martinez': str(round((ultimos_valores[11] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_martinez': formatear_dinero(ultimos_valores[11] - ultimos_valores[9]),
               'conf_alanis_martinez': str(round((ultimos_valores[11] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",

                #


               'dif_anses_alanis_ipc': formatear_dinero(ultimos_valores[12] - ultimos_valores[0]),
               'conf_anses_alanis_ipc': str(round((ultimos_valores[12] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",

               'dif_caliva_alanis_ipc': formatear_dinero(ultimos_valores[12] - ultimos_valores[7]),
               'conf_caliva_alanis_ipc': str(round((ultimos_valores[12] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_alanis_ipc': formatear_dinero(ultimos_valores[12] - ultimos_valores[9]),
               'conf_alanis_alanis_ipc': str(round((ultimos_valores[12] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",

                #

               'dif_anses_alanis_ripte': formatear_dinero(ultimos_valores[13] - ultimos_valores[0]),
               'conf_anses_alanis_ripte': str(round((ultimos_valores[13] - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",

               'dif_caliva_alanis_ripte': formatear_dinero(ultimos_valores[13] - ultimos_valores[7]),
               'conf_caliva_alanis_ripte': str(round((ultimos_valores[13] - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_alanis_ripte': formatear_dinero(ultimos_valores[13] - ultimos_valores[9]),
               'conf_alanis_alanis_ripte': str(round((ultimos_valores[13] - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",

               #

               'dif_anses_movilidad_personalizada': formatear_dinero(ultimo_valor_personalizado - ultimos_valores[0]),
               'conf_anses_movilidad_personalizada': str(round((ultimo_valor_personalizado - ultimos_valores[0]) / ultimos_valores[0] * 100, 2)) + "%",

               'dif_caliva_movilidad_personalizada': formatear_dinero(ultimo_valor_personalizado - ultimos_valores[7]),
               'conf_caliva_movilidad_personalizada': str(round((ultimo_valor_personalizado - ultimos_valores[7]) / ultimos_valores[7] * 100, 2)) + "%",
               'dif_alanis_movilidad_personalizada': formatear_dinero(ultimo_valor_personalizado - ultimos_valores[9]),
               'conf_alanis_movilidad_personalizada': str(round((ultimo_valor_personalizado - ultimos_valores[9]) / ultimos_valores[9] * 100, 2)) + "%",
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
        if self.fallo_martinez:
            datos.append(ultimos_valores[11])
            #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
            etiquetas.append('Fallo Martinez')
        if self.alanis_ipc:
            datos.append(ultimos_valores[12])
            #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
            etiquetas.append('Alanis con IPC')
        if self.alanis_ripte:
            datos.append(ultimos_valores[13])
            #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
            etiquetas.append('Alanis con RIPTE')
        if self.movilidad_personalizada:
            datos.append(ultimo_valor_personalizado)
            #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
            etiquetas.append('Movilidad personalizada')
        grafico1 = crear_graficos(datos,etiquetas, "Haber a la fecha de cierre")

        if self.comparacion_mov_caliva:
                datos_2 = [ultimos_valores[0], ultimos_valores[7]]
                etiquetas_2 = ['Anses','Movilidad de Sentencia (Caliva)']
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
                #if self.Alanis_Mas_Anses:
                    #datos_2.append(ultimos_valores[9])
                    #datos_2.append(round(ultimos_valores[9] - ultimos_valores[4],2))
                    #etiquetas_2.append('Alanis mas Anses')
                if self.Alanis_con_27551_con_3_meses_rezago:
                    datos_2.append(ultimos_valores[10])
                    #datos_2.append(round(ultimos_valores[10] - ultimos_valores[4],2))
                    etiquetas_2.append('Alanis con 27551 con 3 rezago')
                if self.fallo_martinez:
                    datos_2.append(ultimos_valores[11])
                    #datos_2.append(round(ultimos_valores[10] - ultimos_valores[4],2))
                    etiquetas_2.append('Fallo Martinez')
                if self.alanis_ipc:
                    datos_2.append(ultimos_valores[12])
                    #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
                    etiquetas_2.append('Alanis con IPC')
                if self.alanis_ripte:
                    datos_2.append(ultimos_valores[13])
                    #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
                    etiquetas_2.append('Alanis con RIPTE')
                if self.movilidad_personalizada:
                    datos_2.append(ultimo_valor_personalizado)
                    #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
                    etiquetas_2.append('Movilidad personalizada')
                grafico2 = crear_graficos(datos_2, etiquetas_2, "Haber a la fecha de cierre")
        else:
            grafico2 = None
        if self.comparacion_mov_alanis:
                datos_3 = [ultimos_valores[0], ultimos_valores[9]]
                etiquetas_3 = ['Anses','Movilidad de Sentencia (Alanis)']
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
                if self.fallo_martinez:
                    datos_3.append(ultimos_valores[11])
                    #datos_2.append(round(ultimos_valores[10] - ultimos_valores[4],2))
                    etiquetas_3.append('Fallo Martinez')
                if self.alanis_ipc:
                    datos_3.append(ultimos_valores[12])
                    #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
                    etiquetas_3.append('Alanis con IPC')
                if self.alanis_ripte:
                    datos_3.append(ultimos_valores[13])
                    #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
                    etiquetas_3.append('Alanis con RIPTE')
                if self.movilidad_personalizada:
                    datos_3.append(ultimo_valor_personalizado)
                    #datos.append(round(ultimos_valores[10] - ultimos_valores[0],2))
                    etiquetas_3.append('Movilidad personalizada')
                grafico3 = crear_graficos(datos_3, etiquetas_3, "Haber a la fecha de cierre")
        else:
            grafico3 = None

        return filas_dinero,ultimo_valor_personalizado, lista_filas, grafico1, grafico2, grafico3, diccionario_comparacion, ultimos_valores

    def generar_pdf(self):
        filas_dinero,ultimo_valor_personalizado, lista_filas, grafico1, grafico2,grafico3, diccionario_comparacion, montos_a_fecha_cierre = self.obtener_datos()
        lista_filas = [fila + (dinero,) for fila, dinero in zip(lista_filas, filas_dinero)]

        grafico_4 = generar_grafico_linea(lista_filas, self.ipc, self.ripte, self.uma, self.movilidad_sentencia, self.Ley_27426_rezago, self.caliva_mas_anses, self.Caliva_Marquez_con_27551_con_3_rezago, self.Caliva_Marquez_con_27551_con_6_rezago, self.Alanis_Mas_Anses, self.Alanis_con_27551_con_3_meses_rezago, self.fallo_martinez, self.alanis_ipc, self.alanis_ripte,self.movilidad_personalizada ,self.datos_del_actor, filas_dinero)
        # Extraer fechas y montos de lista_fila

        rendered = render_template(
            'calculadora_movilidad/resultado_calculadora_movilidad.html',
            filas=lista_filas, 
            comparacion=diccionario_comparacion, 
            grafico1 = grafico1,
            grafico2 = grafico2,
            grafico3 = grafico3,
            grafico4 = grafico_4,
            monto = formatear_dinero(self.monto),
            datos_del_actor = self.datos_del_actor,
            fallecido = self.fallecido,
            fecha_fallecimiento = transformar_fecha(self.fecha_fallecimiento),
            cobrador_pension = self.cobrador_pension,
            expediente = self.expediente,
            cuil_expediente = self.cuil_expediente,
            beneficio = self.beneficio,
            num_beneficio = self.num_beneficio,
            fecha_inicio = convertir_fecha_periodo(self.fecha_inicio),
            fecha_fin = convertir_fecha_periodo(self.fecha_fin),
            haber = self.haber,
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
            fallo_martinez = self.fallo_martinez,
            alanis_ipc = self.alanis_ipc,
            alanis_ripte = self.alanis_ripte,
            comparacion_mov_sentencia_si = self.comparacion_mov_sentencia_si,
            comparacion_mov_caliva= self.comparacion_mov_caliva,
            comparacion_mov_alanis= self.comparacion_mov_alanis,
            movilidad_personalizada = self.movilidad_personalizada,
            movilidad_aplicada = self.resultado,
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
            valor_Alanis_con_27551_con_3_rezago = formatear_dinero(montos_a_fecha_cierre[10]),
            valor_fallo_martinez = formatear_dinero(montos_a_fecha_cierre[11]),
            valor_alanis_ipc = formatear_dinero(montos_a_fecha_cierre[12]),
            valor_alanis_ripte = formatear_dinero(montos_a_fecha_cierre[13]),
            valor_mov_personalizada = formatear_dinero(ultimo_valor_personalizado)




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