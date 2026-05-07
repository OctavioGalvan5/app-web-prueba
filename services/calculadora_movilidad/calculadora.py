import base64
from datetime import datetime, date
from decimal import Decimal
from io import BytesIO

import plotly.graph_objects as go
from dateutil.relativedelta import relativedelta
from flask import render_template, send_file
from sqlalchemy import text
from xhtml2pdf import pisa

from models.database import engine
from services.calculos import formatear_dinero, transformar_fecha

# Columnas DB en orden. El índice aquí define el índice en lista_montos/ultimos_valores (0-16).
COLUMNAS_DB = [
    'ANSES',                                       # 0
    'IPC',                                         # 1
    'RIPTE',                                       # 2
    'UMA',                                         # 3
    'alanis_ipc',                                  # 4  (movilidad_sentencia)
    'Ley_27426_IPC_RIPTE_Trimestral_Diferido_3M',  # 5
    'Caliva_Marquez_con_27551_con_3_rezago',       # 6
    'Caliva_mas_Anses',                            # 7
    'alanis_ripte',                                # 8  (Caliva_Marquez_con_27551_con_6_rezago)
    'Alanis_Mas_Anses',                            # 9
    'Alanis_con_27551_con_3_meses_rezago',         # 10
    'martinez',                                    # 11
    'alanis_ipc',                                  # 12 (flag alanis_ipc — misma col que 4)
    'alanis_ripte',                                # 13 (flag alanis_ripte — misma col que 8)
    'Caliva_Palavecino',                           # 14
    'Anses_Palavecino',                            # 15
    'Alanis_Colina',                               # 16
]

# Índices de COLUMNAS_DB que reciben el bono +$1500 cuando id == 243 (marzo 2020)
_BONO_243 = frozenset({0, 11, 15})  # ANSES, martinez, Anses_Palavecino

# ---------------------------------------------------------------------------
# Registro de métodos seleccionables — FUENTE DE VERDAD ÚNICA
# Para agregar un nuevo índice: agregar una entrada aquí + columna en la DB.
# form_key  → name del checkbox en el formulario HTML
# idx       → posición en COLUMNAS_DB (debe coincidir exactamente)
# label     → texto que ve el usuario
# ---------------------------------------------------------------------------
METODOS_SELECCIONABLES = [
    {'form_key': 'ipc',                                  'idx': 1,  'label': 'IPC — Precios al Consumidor'},
    {'form_key': 'ripte',                                'idx': 2,  'label': 'RIPTE — Rem. Imponible Promedio Trabajadores Estables'},
    {'form_key': 'uma',                                  'idx': 3,  'label': 'UMA — Poder Judicial de la Nación'},
    {'form_key': 'caliva_mas_anses',                     'idx': 7,  'label': 'Caliva más ANSES'},
    {'form_key': 'Alanis_Mas_Anses',                     'idx': 9,  'label': 'Alanis más ANSES'},
    {'form_key': 'alanis_ipc',                           'idx': 12, 'label': 'Alanis con IPC'},
    {'form_key': 'alanis_ripte',                         'idx': 13, 'label': 'Alanis con RIPTE'},
    {'form_key': 'Alanis_con_27551_con_3_meses_rezago',  'idx': 10, 'label': 'Alanis 27551 — 3 meses rezago'},
    {'form_key': 'Alanis_Colina',                        'idx': 16, 'label': 'Alanis con Colina'},
    {'form_key': 'Caliva_Palavecino',                    'idx': 14, 'label': 'Caliva más Palavecino'},
    {'form_key': 'Anses_Palavecino',                     'idx': 15, 'label': 'ANSES más Palavecino'},
    {'form_key': 'fallo_martinez',                       'idx': 11, 'label': 'Fallo Martínez'},
    {'form_key': 'Ley_27426_rezago',                     'idx': 5,  'label': 'Ley 27426 con rezago'},
    {'form_key': 'Caliva_Marquez_con_27551_con_3_rezago','idx': 6,  'label': 'Caliva más Cendán'},
    {'form_key': 'Caliva_Marquez_con_27551_con_6_rezago','idx': 8,  'label': 'Caliva Márquez 27551 — 6 meses rezago'},
]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _to_date(valor):
    """Normaliza str / datetime / date a datetime.date."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.strptime(valor, '%Y-%m-%d').date()


def _build_fila(fecha, montos):
    """Tupla (periodo_str, monto_formateado, ...) para lista_filas."""
    return (convertir_fecha_periodo(fecha),) + tuple(formatear_dinero(m) for m in montos)


# ---------------------------------------------------------------------------
# Funciones de fecha / formato
# ---------------------------------------------------------------------------

def convertir_fecha_periodo(fecha):
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d')
    return fecha.strftime('%m/%Y')


def transformar_fecha_2(fecha):
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    except ValueError:
        try:
            fecha_obj = datetime.strptime(fecha, '%m/%Y')
        except ValueError:
            raise ValueError(f"Formato de fecha no válido: {fecha}")
    return fecha_obj.strftime('%m/%Y')


# ---------------------------------------------------------------------------
# Helpers de texto (sin cambios lógicos)
# ---------------------------------------------------------------------------

def procesar_tupla_reajuste(tupla, haber_reajustado, monto, fecha_inicio):
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Formato de fecha inválido. Se esperaba 'YYYY-MM-DD'.")

    resultado = "Se parte de un Haber Percibido de {} Pesos del {} ".format(
        formatear_dinero(monto),
        fecha_inicio.strftime('%d/%m/%Y')
    )

    bandera = 0
    if haber_reajustado:
        for elemento in tupla:
            if elemento[0] is not None:
                monto_reajuste = elemento[1]
                fecha_reajuste = elemento[0]
                if isinstance(fecha_reajuste, str):
                    try:
                        fecha_reajuste = datetime.strptime(fecha_reajuste, '%Y-%m-%d')
                    except ValueError:
                        raise ValueError("Formato de fecha inválido. Se esperaba 'YYYY-MM-DD'.")
                if bandera == 0:
                    resultado += " que el " + fecha_reajuste.strftime('%d/%m/%Y') + " fué reajustado a " + formatear_dinero(monto_reajuste)
                    bandera = 1
                else:
                    resultado += " y luego el " + fecha_reajuste.strftime('%d/%m/%Y') + " fué reajustado a " + formatear_dinero(monto_reajuste)

    return resultado.strip()


def procesar_tuplas(tuplas, movilidad_1):
    diccionario = {
        'Aumentos_Anses': 'Aumentos Generales de la ANSeS por movilidad',
        'Salarios_Nivel_General_INDEC': 'Salarios Nivel General INDEC',
        'Aumento_de_Marzo_2018_Ley_26417_14': 'Aumento de Marzo 2018 Ley 26417 14%',
        'Aumentos_fallo_Marquez_Raimundo_por_Ley_27551': 'Aumentos fallo Marquez, Raimundo por Ley 27551',
        'Aumentos_fallo_Alanis_Daniel_Ley_27551_35_55_2020': 'Aumentos fallo Alanis, Daniel Ley 27551 35,55% para el año 2020',
        'RIPTE_Remuneracion_Imponible_Promedio_Trabajadores_Estables': 'RIPTE (Remuneración Imponible Promedio de Trabajadores Estables)',
        'RIPTE_Trimestral_Retrasado_3_Meses': 'RIPTE trimestral retrasado 3 meses',
        'RIPTE_Retrasado_2_Meses': 'RIPTE retrasado 2 meses',
        'IPC_Retrasado_2_Meses': 'IPC retrasado 2 meses',
        'IPC_Retrasado_3_Meses': 'IPC retrasado 3 meses',
        'Ley_27551_50_IPC_50_RIPTE_Trimestral_Retrasado_3_Meses': 'Ley 27551 (50 % IPC y 50% RIPTE Trimestral retrasado 3 meses)',
        'Sin_Movilidad': 'Sin Movilidad',
        'Aumentos_Poder_Judicial_de_la_Nacion': 'Aumentos Poder Judicial de la Nacion',
        'IPC_Precios_Consumidor': 'Precios al Consumidor o Costo de Vida (I.P.C.)',
        'Salarios_Nivel_General_INDEC_Anual': 'Salarios Nivel General INDEC Anual',
        'Ley_27426_IPC_RIPTE_Trimestral_Diferido_3M': 'Ley 27426 - IPC y Ripte Trimestral Diferido 3 meses',
        'Aumentos_fallo_Martinez': 'Aumentos Fallo Martinez para el año 2020',
    }
    resultado = diccionario[movilidad_1]

    for elemento in tuplas:
        if elemento[0] is not None:
            clave = elemento[1]
            fecha = elemento[0]
            if clave in diccionario:
                if resultado != "":
                    resultado += " hasta el " + fecha.strftime('%d/%m/%Y') + " y desde ahi " + diccionario[clave]

    return resultado.strip()


# ---------------------------------------------------------------------------
# Cálculo de movilidad personalizada — optimizado: 1 query para todo el rango
# ---------------------------------------------------------------------------

def funcion_movilidad_personalizada(fecha_inicial, columna, monto, fecha_final, tupla_reajuste):
    fecha_inicio_dt = _to_date(fecha_inicial) + relativedelta(months=1)
    fecha_final_dt = _to_date(fecha_final)

    # Construir lookup de cambio de columna: (year, month) → nueva columna
    cambios_columna = {}
    for ajuste in tupla_reajuste:
        if ajuste[0] is not None:
            f = _to_date(ajuste[0]) + relativedelta(months=1)
            cambios_columna[(f.year, f.month)] = ajuste[1]

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT * FROM indices_de_movilidad
                WHERE fechas BETWEEN :f_ini AND :f_fin
                ORDER BY fechas ASC
            """),
            {"f_ini": fecha_inicio_dt, "f_fin": fecha_final_dt}
        )
        keys = list(result.keys())
        rows = result.fetchall()

    if not rows:
        return [], []

    monto_actual = Decimal(str(monto))
    columna_actual = columna
    resultados = []
    resultado_dinero = []

    for fila_raw in rows:
        fd = dict(zip(keys, fila_raw))
        fecha_fila = _to_date(fd['fechas'])

        valor = fd.get(columna_actual)
        if valor is not None:
            monto_actual *= Decimal(str(valor))

        # Bono marzo 2020 para columna ANSES
        if fecha_fila == date(2020, 3, 1) and columna_actual == 'Aumentos_Anses':
            monto_actual += Decimal('1500')

        resultados.append(monto_actual)
        resultado_dinero.append(formatear_dinero(monto_actual))

        # Cambio de columna si corresponde
        clave = (fecha_fila.year, fecha_fila.month)
        if clave in cambios_columna:
            columna_actual = cambios_columna[clave]

    return resultados, resultado_dinero


# ---------------------------------------------------------------------------
# Cálculo de todas las metodologías — optimizado: 2 queries por llamada total
# ---------------------------------------------------------------------------

def buscar_fechas(fecha_inicio, fecha_fin, monto, tupla_reajuste, haber_reajustado, fallecido, fecha_fallecimiento):
    fecha_inicio_dt = _to_date(fecha_inicio) + relativedelta(months=1)
    fecha_fin_dt = _to_date(fecha_fin)
    # fecha_fallecimiento se adelanta 1 mes, igual que el código original
    fecha_fall_dt = (_to_date(fecha_fallecimiento) + relativedelta(months=1)) if fallecido else None

    monto_d = Decimal(str(monto))

    with engine.connect() as conn:
        # Fila de arranque: fecha más cercana <= fecha_inicio_dt
        result = conn.execute(
            text("SELECT * FROM tabla_movilidades WHERE fechas <= :f ORDER BY fechas DESC LIMIT 1"),
            {"f": fecha_inicio_dt}
        )
        fila_menor = result.fetchone()
        if fila_menor is None:
            print("No se encontró una fecha menor a la ingresada.")
            return [], []

        keys = list(result.keys())
        fd = dict(zip(keys, fila_menor))
        montos = [monto_d * Decimal(str(fd[col])) for col in COLUMNAS_DB]

        lista_filas = [_build_fila(fd['fechas'], montos)]
        lista_montos = [tuple(montos)]

        # Todas las filas posteriores en un solo query
        result2 = conn.execute(
            text("SELECT * FROM tabla_movilidades WHERE fechas > :f ORDER BY fechas ASC"),
            {"f": fecha_inicio_dt}
        )
        keys2 = list(result2.keys())
        filas_mayores = result2.fetchall()

    if not filas_mayores:
        print("No se encontraron filas con fechas mayores a la ingresada.")
        return lista_filas, lista_montos

    for fila_raw in filas_mayores:
        fd = dict(zip(keys2, fila_raw))
        fecha_fila = _to_date(fd['fechas'])
        es_243 = fd['id'] == 243
        es_fallecimiento = (
            fallecido and fecha_fall_dt is not None
            and fecha_fila.year == fecha_fall_dt.year
            and fecha_fila.month == fecha_fall_dt.month
        )

        nuevos = []
        for i, col in enumerate(COLUMNAS_DB):
            v = montos[i] * Decimal(str(fd[col]))

            # Bono marzo 2020 (+$1500) para ANSES, martinez y Anses_Palavecino
            if es_243 and i in _BONO_243:
                v += Decimal('1500')

            if es_fallecimiento:
                # Mes de fallecimiento: reducción al 70%
                v *= Decimal('0.7')
            elif i == 0 and haber_reajustado:
                # Haber reajustado: reemplazar ANSES por el valor absoluto de la tupla
                for elem in tupla_reajuste:
                    if elem[0] is not None and fecha_fila.year == elem[0].year and fecha_fila.month == elem[0].month:
                        v = Decimal(str(elem[1]))
                        break

            nuevos.append(v)

        montos = nuevos
        lista_filas.append(_build_fila(fd['fechas'], montos))
        lista_montos.append(tuple(montos))

        if fecha_fila.year == fecha_fin_dt.year and fecha_fila.month == fecha_fin_dt.month:
            break

    return lista_filas, lista_montos


# ---------------------------------------------------------------------------
# Diccionario de comparación — extraído para reutilización API
# ---------------------------------------------------------------------------

def _calcular_comparacion(ultimos_valores, ultimo_valor_personalizado):
    uv = ultimos_valores  # alias corto

    def dif(a, b):
        return formatear_dinero(uv[b] - uv[a])

    def conf(a, b):
        return str(round((uv[b] - uv[a]) / uv[a] * 100, 2)) + "%"

    def dif_p(a):
        return formatear_dinero(ultimo_valor_personalizado - uv[a])

    def conf_p(a):
        return str(round((ultimo_valor_personalizado - uv[a]) / uv[a] * 100, 2)) + "%"

    return {
        'dif_anses_ipc': dif(0, 1),
        'conf_anses_ipc': conf(0, 1),
        'dif_sent_ipc': dif(4, 1),
        'conf_sent_ipc': conf(4, 1),
        'dif_caliva_ipc': dif(7, 1),
        'conf_caliva_ipc': conf(7, 1),
        'dif_alanis_ipc': dif(9, 1),
        'conf_alanis_ipc': conf(9, 1),

        'dif_anses_ripte': dif(0, 2),
        'conf_anses_ripte': conf(0, 2),
        'dif_sent_ripte': dif(4, 2),
        'conf_sent_ripte': conf(4, 2),
        'dif_caliva_ripte': dif(7, 2),
        'conf_caliva_ripte': conf(7, 2),
        'dif_alanis_ripte': dif(9, 2),
        'conf_alanis_ripte': conf(9, 2),

        'dif_anses_UMA': dif(0, 3),
        'conf_anses_UMA': conf(0, 3),
        'dif_sent_UMA': dif(4, 3),
        'conf_sent_UMA': conf(4, 3),
        'dif_caliva_UMA': dif(7, 3),
        'conf_caliva_UMA': conf(7, 3),
        'dif_alanis_UMA': dif(9, 3),
        'conf_alanis_UMA': conf(9, 3),

        'dif_anses_sent': dif(0, 4),
        'conf_anses_sent': conf(0, 4),

        'dif_anses_ley27426': dif(0, 5),
        'conf_anses_ley27426': conf(0, 5),
        'dif_sent_ley27426': dif(4, 5),
        'conf_sent_ley27426': conf(4, 5),
        'dif_caliva_ley27426': dif(7, 5),
        'conf_caliva_ley27426': conf(7, 5),
        'dif_alanis_ley27426': dif(9, 5),
        'conf_alanis_ley27426': conf(9, 5),

        'dif_anses_Caliva_Marquez_con_27551_con_3_rezago': dif(0, 6),
        'conf_anses_Caliva_Marquez_con_27551_con_3_rezago': conf(0, 6),
        'dif_sent_Caliva_Marquez_con_27551_con_3_rezago': dif(4, 6),
        'conf_sent_Caliva_Marquez_con_27551_con_3_rezago': conf(4, 6),
        'dif_caliva_Caliva_Marquez_con_27551_con_3_rezago': dif(7, 6),
        'conf_caliva_Caliva_Marquez_con_27551_con_3_rezago': conf(7, 6),
        'dif_alanis_Caliva_Marquez_con_27551_con_3_rezago': dif(9, 6),
        'conf_alanis_Caliva_Marquez_con_27551_con_3_rezago': conf(9, 6),

        'dif_anses_caliva_mas_anses': dif(0, 7),
        'conf_anses_caliva_mas_anses': conf(0, 7),
        'dif_sent_caliva_mas_anses': dif(4, 7),
        'conf_sent_caliva_mas_anses': conf(4, 7),
        'dif_alanis_caliva_mas_anses': dif(9, 7),
        'conf_alanis_caliva_mas_anses': conf(9, 7),

        'dif_anses_Caliva_Marquez_con_27551_con_6_rezago': dif(0, 8),
        'conf_anses_Caliva_Marquez_con_27551_con_6_rezago': conf(0, 8),
        'dif_sent_Caliva_Marquez_con_27551_con_6_rezago': dif(4, 8),
        'conf_sent_Caliva_Marquez_con_27551_con_6_rezago': conf(4, 8),

        'dif_anses_alanis_mas_anses': dif(0, 9),
        'conf_anses_alanis_mas_anses': conf(0, 9),
        'dif_sent_alanis_mas_anses': dif(4, 9),
        'conf_sent_alanis_mas_anses': conf(4, 9),

        'dif_anses_Alanis_con_27551_con_3_rezago': dif(0, 10),
        'conf_anses_Alanis_con_27551_con_3_rezago': conf(0, 10),
        'dif_sent_Alanis_con_27551_con_3_rezago': dif(4, 10),
        'conf_sent_Alanis_con_27551_con_3_rezago': conf(4, 10),
        'dif_caliva_Alanis_con_27551_con_3_rezago': dif(7, 10),
        'conf_caliva_Alanis_con_27551_con_3_rezago': conf(7, 10),
        'dif_alanis_Alanis_con_27551_con_3_rezago': dif(9, 10),
        'conf_alanis_Alanis_con_27551_con_3_rezago': conf(9, 10),

        'dif_anses_martinez': dif(0, 11),
        'conf_anses_martinez': conf(0, 11),
        'dif_caliva_martinez': dif(7, 11),
        'conf_caliva_martinez': conf(7, 11),
        'dif_alanis_martinez': dif(9, 11),
        'conf_alanis_martinez': conf(9, 11),

        'dif_anses_alanis_ipc': dif(0, 12),
        'conf_anses_alanis_ipc': conf(0, 12),
        'dif_caliva_alanis_ipc': dif(7, 12),
        'conf_caliva_alanis_ipc': conf(7, 12),
        'dif_alanis_alanis_ipc': dif(9, 12),
        'conf_alanis_alanis_ipc': conf(9, 12),

        'dif_anses_alanis_ripte': dif(0, 13),
        'conf_anses_alanis_ripte': conf(0, 13),
        'dif_caliva_alanis_ripte': dif(7, 13),
        'conf_caliva_alanis_ripte': conf(7, 13),
        'dif_alanis_alanis_ripte': dif(9, 13),
        'conf_alanis_alanis_ripte': conf(9, 13),

        'dif_anses_movilidad_personalizada': dif_p(0),
        'conf_anses_movilidad_personalizada': conf_p(0),
        'dif_caliva_movilidad_personalizada': dif_p(7),
        'conf_caliva_movilidad_personalizada': conf_p(7),
        'dif_alanis_movilidad_personalizada': dif_p(9),
        'conf_alanis_movilidad_personalizada': conf_p(9),

        'dif_anses_Caliva_Palavecino': dif(0, 14),
        'conf_anses_Caliva_Palavecino': conf(0, 14),
        'dif_caliva_Caliva_Palavecino': dif(7, 14),
        'conf_caliva_Caliva_Palavecino': conf(7, 14),
        'dif_alanis_Caliva_Palavecino': dif(9, 14),
        'conf_alanis_Caliva_Palavecino': conf(9, 14),

        'dif_anses_Anses_Palavecino': dif(0, 15),
        'conf_anses_Anses_Palavecino': conf(0, 15),
        'dif_caliva_Anses_Palavecino': dif(7, 15),
        'conf_caliva_Anses_Palavecino': conf(7, 15),
        'dif_alanis_Anses_Palavecino': dif(9, 15),
        'conf_alanis_Anses_Palavecino': conf(9, 15),

        'dif_anses_Alanis_Colina': dif(0, 16),
        'conf_anses_Alanis_Colina': conf(0, 16),
        'dif_caliva_Alanis_Colina': dif(7, 16),
        'conf_caliva_Alanis_Colina': conf(7, 16),
        'dif_alanis_Alanis_Colina': dif(9, 16),
        'conf_alanis_Alanis_Colina': conf(9, 16),
    }


# ---------------------------------------------------------------------------
# Gráficos (sin cambios lógicos)
# ---------------------------------------------------------------------------

def generar_grafico_linea(
    lista_filas_bf,
    metodos_seleccionados,
    datos_mov_personalizada, movilidad_personalizada_flag,
    titulo
):
    fechas = [transformar_fecha_2(fila[0]) for fila in lista_filas_bf]
    montos_bf = list(zip(*[fila[1:] for fila in lista_filas_bf]))

    # ANSES siempre se incluye (índice 0); el resto según selección
    indices_a_incluir = {0: 'ANSES'}
    for m in METODOS_SELECCIONABLES:
        if m['form_key'] in metodos_seleccionados:
            indices_a_incluir[m['idx']] = m['label']

    fig = go.Figure()

    def _parse_money(m):
        return float(str(m).replace('$', '').replace(' ', '').replace('.', '').replace(',', '.'))

    for i, serie in enumerate(montos_bf):
        if i in indices_a_incluir:
            fig.add_trace(go.Scatter(
                x=fechas,
                y=[_parse_money(m) for m in serie],
                mode='lines',
                name=indices_a_incluir[i]
            ))

    if movilidad_personalizada_flag:
        fig.add_trace(go.Scatter(
            x=fechas,
            y=[_parse_money(m) for m in datos_mov_personalizada],
            mode='lines',
            name='Movilidad Personalizada'
        ))

    fig.update_layout(
        title='Acreditacion del Daño del haber de ' + titulo,
        xaxis_title='Fecha',
        yaxis_title='Monto ($)',
        legend_title='Conceptos',
        xaxis=dict(type='category'),
        yaxis=dict(tickformat=',.0f', title='Monto ($)'),
        template='plotly_white',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
    )

    try:
        imagen_base64 = base64.b64encode(fig.to_image(format="png")).decode('utf-8')
    except Exception as e:
        print("⚠️ Error al generar grafico4:", e)
        imagen_base64 = ""

    return imagen_base64


def crear_graficos(datos, etiquetas, titulo):
    resultados = list(map(formatear_dinero, datos))
    fig = go.Figure(data=go.Bar(
        x=etiquetas,
        y=datos,
        marker_color=['#7671FA','#00c4ff','#E5EAF3','#07244C','#178DAD','#7E7F9C',
                      '#9e73a3','#3cd7c4','#83007f','#bb73b3','#5F9EA0','#4682B4',
                      '#DA70D6','#20B2AA','#CD5C5C','#FFA07A','#BA55D3','#6495ED',
                      '#98FB98','#FFD700'],
        text=resultados, textposition='auto',
        textfont=dict(size=14)
    ))
    fig.add_shape(
        type="line",
        x0=-0.5, x1=len(etiquetas) - 0.5,
        y0=datos[0], y1=datos[0],
        line=dict(color="red", width=3, dash="solid")
    )
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=20), x=0, xanchor='left'),
        xaxis_title='Categorías', yaxis_title='Monto ($)',
        plot_bgcolor='rgba(0, 0, 0, 0)', paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=40, r=40, t=60, b=40),
        width=800, height=600,
        xaxis=dict(title_font=dict(size=14), tickfont=dict(size=10)),
        yaxis=dict(title_font=dict(size=14), tickfont=dict(size=12))
    )
    return base64.b64encode(fig.to_image(format="png")).decode('utf-8')


# ---------------------------------------------------------------------------
# API pública — función pura sin dependencias Flask
# ---------------------------------------------------------------------------

def calcular_movilidad(params: dict) -> dict:
    """
    Calcula la movilidad y retorna todos los datos como dict puro (sin Flask).
    Puede ser llamada desde otros servicios internos directamente.

    Claves requeridas en params:
        fecha_inicio, fecha_fin, monto, movilidad_1, tupla

    Claves opcionales:
        tupla_reajuste (default []), haber_reajustado (default False),
        fallecido (default False), fecha_fallecimiento (default = fecha_fin)

    Retorna dict con:
        lista_filas, lista_montos, filas_dinero, ultimo_valor_personalizado,
        ultimos_valores, diccionario_comparacion
    """
    fecha_inicio = params['fecha_inicio']
    fecha_fin = params['fecha_fin']
    monto = params['monto']
    movilidad_1 = params['movilidad_1']
    tupla = params['tupla']
    tupla_reajuste = params.get('tupla_reajuste', [])
    haber_reajustado = params.get('haber_reajustado', False)
    fallecido = params.get('fallecido', False)
    fecha_fallecimiento = params.get('fecha_fallecimiento', fecha_fin)

    filas_personalizada, filas_dinero = funcion_movilidad_personalizada(
        fecha_inicio, movilidad_1, monto, fecha_fin, tupla
    )
    ultimo_valor_personalizado = filas_personalizada[-1] if filas_personalizada else Decimal('0')

    lista_filas, lista_montos = buscar_fechas(
        fecha_inicio, fecha_fin, monto, tupla_reajuste,
        haber_reajustado, fallecido, fecha_fallecimiento
    )

    if not lista_montos:
        return {}

    ultimos_valores = lista_montos[-1]
    diccionario_comparacion = _calcular_comparacion(ultimos_valores, ultimo_valor_personalizado)

    return {
        'lista_filas': lista_filas,
        'lista_montos': lista_montos,
        'filas_dinero': filas_dinero,
        'ultimo_valor_personalizado': ultimo_valor_personalizado,
        'ultimos_valores': ultimos_valores,
        'diccionario_comparacion': diccionario_comparacion,
    }


# ---------------------------------------------------------------------------
# Clase principal — delega en calcular_movilidad y agrega capa Flask
# ---------------------------------------------------------------------------

class CalculadorMovilidad:
    def __init__(self, datos_del_actor, fallecido, fecha_fallecimiento, cobrador_pension,
                 expediente, cuil_expediente, beneficio, num_beneficio,
                 fecha_inicio, fecha_fin, fecha_adquisicion_del_derecho, monto,
                 metodos_seleccionados,
                 comparacion_mov_sentencia_si, comparacion_mov_sentencia_no,
                 comparacion_mov_caliva, comparacion_mov_alanis,
                 movilidad_personalizada, movilidad_1, tupla, tupla_reajuste, haber_reajustado):
        """
        metodos_seleccionados: set de form_key strings (ej: {'ipc', 'ripte', 'uma'})
        """
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
        self.metodos_seleccionados = metodos_seleccionados

        # Flags individuales derivados del set — compatibilidad con el template de resultado
        def _sel(key):
            return key in metodos_seleccionados

        self.ipc = _sel('ipc')
        self.ripte = _sel('ripte')
        self.uma = _sel('uma')
        self.movilidad_sentencia = False  # no es checkbox directo, siempre calculado
        self.Ley_27426_rezago = _sel('Ley_27426_rezago')
        self.caliva_mas_anses = _sel('caliva_mas_anses')
        self.Caliva_Marquez_con_27551_con_3_rezago = _sel('Caliva_Marquez_con_27551_con_3_rezago')
        self.Caliva_Marquez_con_27551_con_6_rezago = _sel('Caliva_Marquez_con_27551_con_6_rezago')
        self.Alanis_Mas_Anses = _sel('Alanis_Mas_Anses')
        self.Alanis_con_27551_con_3_meses_rezago = _sel('Alanis_con_27551_con_3_meses_rezago')
        self.fallo_martinez = _sel('fallo_martinez')
        self.alanis_ipc = _sel('alanis_ipc')
        self.alanis_ripte = _sel('alanis_ripte')
        self.Caliva_Palavecino = _sel('Caliva_Palavecino')
        self.Anses_Palavecino = _sel('Anses_Palavecino')
        self.Alanis_Colina = _sel('Alanis_Colina')

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
        self.haber = procesar_tupla_reajuste(
            self.tupla_reajuste, self.haber_reajustado, self.monto, self.fecha_inicio
        )

    def _build_grafico_comparacion(self, ultimos_valores, ultimo_valor_personalizado, base_idx, base_label):
        """Construye lista de datos/etiquetas para gráficos de comparación (grafico2/grafico3)."""
        uv = ultimos_valores
        datos = [uv[0], uv[base_idx]]
        etiquetas = ['Anses', base_label]

        for m in METODOS_SELECCIONABLES:
            if m['form_key'] in self.metodos_seleccionados and m['idx'] != base_idx:
                datos.append(uv[m['idx']])
                etiquetas.append(m['label'])
        if self.movilidad_personalizada:
            datos.append(ultimo_valor_personalizado)
            etiquetas.append('Movilidad personalizada')

        return datos, etiquetas

    def obtener_datos(self):
        resultado = calcular_movilidad({
            'fecha_inicio': self.fecha_inicio,
            'fecha_fin': self.fecha_fin,
            'monto': self.monto,
            'movilidad_1': self.movilidad_1,
            'tupla': self.tupla,
            'tupla_reajuste': self.tupla_reajuste,
            'haber_reajustado': self.haber_reajustado,
            'fallecido': self.fallecido,
            'fecha_fallecimiento': self.fecha_fallecimiento,
        })

        filas_dinero = resultado['filas_dinero']
        ultimo_valor_personalizado = resultado['ultimo_valor_personalizado']
        lista_filas = resultado['lista_filas']
        ultimos_valores = resultado['ultimos_valores']
        diccionario_comparacion = resultado['diccionario_comparacion']

        # Gráfico 1 — todos los valores seleccionados
        uv = ultimos_valores
        datos_1 = [uv[0]]
        etiquetas_1 = ['Anses']
        for m in METODOS_SELECCIONABLES:
            if m['form_key'] in self.metodos_seleccionados:
                datos_1.append(uv[m['idx']])
                etiquetas_1.append(m['label'])
        if self.movilidad_personalizada:
            datos_1.append(ultimo_valor_personalizado)
            etiquetas_1.append('Movilidad personalizada')

        grafico1 = crear_graficos(datos_1, etiquetas_1, "Haber a la fecha de cierre")

        grafico2 = None
        if self.comparacion_mov_caliva:
            d2, e2 = self._build_grafico_comparacion(uv, ultimo_valor_personalizado, 7, 'Movilidad de Sentencia (Caliva)')
            grafico2 = crear_graficos(d2, e2, "Haber a la fecha de cierre")

        grafico3 = None
        if self.comparacion_mov_alanis:
            d3, e3 = self._build_grafico_comparacion(uv, ultimo_valor_personalizado, 9, 'Movilidad de Sentencia (Alanis)')
            grafico3 = crear_graficos(d3, e3, "Haber a la fecha de cierre")

        return filas_dinero, ultimo_valor_personalizado, lista_filas, grafico1, grafico2, grafico3, diccionario_comparacion, ultimos_valores

    def generar_pdf(self):
        filas_dinero, ultimo_valor_personalizado, lista_filas, grafico1, grafico2, grafico3, diccionario_comparacion, montos_a_fecha_cierre = self.obtener_datos()
        lista_filas = [fila + (dinero,) for fila, dinero in zip(lista_filas, filas_dinero)]

        grafico_4 = generar_grafico_linea(
            lista_filas,
            self.metodos_seleccionados,
            filas_dinero, self.movilidad_personalizada,
            self.datos_del_actor
        )

        uv = montos_a_fecha_cierre
        rendered = render_template(
            'calculadora_movilidad/resultado_calculadora_movilidad.html',
            filas=lista_filas,
            comparacion=diccionario_comparacion,
            grafico1=grafico1, grafico2=grafico2, grafico3=grafico3, grafico4=grafico_4,
            monto=formatear_dinero(self.monto),
            datos_del_actor=self.datos_del_actor,
            fallecido=self.fallecido,
            fecha_fallecimiento=transformar_fecha(self.fecha_fallecimiento),
            cobrador_pension=self.cobrador_pension,
            expediente=self.expediente,
            cuil_expediente=self.cuil_expediente,
            beneficio=self.beneficio,
            num_beneficio=self.num_beneficio,
            fecha_inicio=convertir_fecha_periodo(self.fecha_inicio),
            fecha_fin=convertir_fecha_periodo(self.fecha_fin),
            haber=self.haber,
            fecha_adquisicion_del_derecho=self.fecha_adquisicion_del_derecho,
            ipc=self.ipc, uma=self.uma, ripte=self.ripte,
            movilidad_sentencia=self.movilidad_sentencia,
            Ley_27426_rezago=self.Ley_27426_rezago,
            caliva_mas_anses=self.caliva_mas_anses,
            Caliva_Marquez_con_27551_con_3_rezago=self.Caliva_Marquez_con_27551_con_3_rezago,
            Caliva_Marquez_con_27551_con_6_rezago=self.Caliva_Marquez_con_27551_con_6_rezago,
            Alanis_Mas_Anses=self.Alanis_Mas_Anses,
            Alanis_con_27551_con_3_meses_rezago=self.Alanis_con_27551_con_3_meses_rezago,
            fallo_martinez=self.fallo_martinez,
            alanis_ipc=self.alanis_ipc,
            alanis_ripte=self.alanis_ripte,
            Caliva_Palavecino=self.Caliva_Palavecino,
            Anses_Palavecino=self.Anses_Palavecino,
            Alanis_Colina=self.Alanis_Colina,
            comparacion_mov_sentencia_si=self.comparacion_mov_sentencia_si,
            comparacion_mov_caliva=self.comparacion_mov_caliva,
            comparacion_mov_alanis=self.comparacion_mov_alanis,
            movilidad_personalizada=self.movilidad_personalizada,
            movilidad_aplicada=self.resultado,
            valor_anses=formatear_dinero(uv[0]),
            valor_ipc=formatear_dinero(uv[1]),
            valor_ripte=formatear_dinero(uv[2]),
            valor_uma=formatear_dinero(uv[3]),
            valor_mov_sentencia=formatear_dinero(uv[4]),
            valor_Ley_27426_rezago=formatear_dinero(uv[5]),
            valor_Caliva_Marquez_con_27551_con_3_rezago=formatear_dinero(uv[6]),
            valor_Caliva_mas_Anses=formatear_dinero(uv[7]),
            valor_Caliva_Marquez_con_27551_con_6_rezago=formatear_dinero(uv[8]),
            valor_Alanis_mas_Anses=formatear_dinero(uv[9]),
            valor_Alanis_con_27551_con_3_rezago=formatear_dinero(uv[10]),
            valor_fallo_martinez=formatear_dinero(uv[11]),
            valor_alanis_ipc=formatear_dinero(uv[12]),
            valor_alanis_ripte=formatear_dinero(uv[13]),
            valor_Caliva_Palavecino=formatear_dinero(uv[14]),
            valor_Anses_Palavecino=formatear_dinero(uv[15]),
            valor_Alanis_Colina=formatear_dinero(uv[16]),
            valor_mov_personalizada=formatear_dinero(ultimo_valor_personalizado),
        )

        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)

        if pisa_status.err:
            return "Error al crear el PDF", 500

        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name='resultado.pdf', mimetype='application/pdf')
