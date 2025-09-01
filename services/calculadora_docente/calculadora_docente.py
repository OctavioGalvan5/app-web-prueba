from models.database import engine
from sqlalchemy import MetaData, Table, select, asc, and_, text
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
from io import BytesIO
from flask import render_template, send_file
from xhtml2pdf import pisa

import base64
import plotly.io as pio  # requiere: pip install -U kaleido

def obtener_indices_docentes(fecha_inicio: str, fecha_fin: str) -> list[Decimal]:
    """
    Devuelve la lista de índices (uno por mes) para el rango:
    del PRIMER día del mes siguiente a `fecha_inicio` hasta el mes de `fecha_fin` (inclusive),
    alineado con `calcular_serie_docente`.
    """
    fi_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    ff_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    start_dt = fi_dt.replace(day=1) + relativedelta(months=1)
    end_dt = ff_dt.replace(day=1)

    metadata = MetaData()
    movilidad_docente = Table("movilidad_docente", metadata, autoload_with=engine)

    with engine.connect() as conn:
        stmt = (
            select(movilidad_docente.c.fechas, movilidad_docente.c.indices_docentes)
            .where(
                and_(
                    movilidad_docente.c.fechas >= start_dt,
                    movilidad_docente.c.fechas <= end_dt,
                )
            )
            .order_by(asc(movilidad_docente.c.fechas))
        )
        rows = conn.execute(stmt).all()

    indices = []
    for fecha, indice in rows:
        try:
            idx_dec = Decimal(str(indice))
        except (InvalidOperation, TypeError, ValueError):
            idx_dec = Decimal("1")
        indices.append(idx_dec)
    return indices

def _fmt_ddmmyyyy(s: str) -> str:
    if not s:
        return ""
    return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")


def mes_anio_es(dt, abreviado=True):
    meses_abbr = [
        "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct",
        "nov", "dic"
    ]
    meses_full = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
        "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    if abreviado:
        return f"{meses_abbr[dt.month-1].capitalize()} {dt.year}"
    return f"{meses_full[dt.month-1]} {dt.year}"


def fig_to_base64_png(fig, scale: int = 2) -> str:
    """Convierte una figura Plotly a PNG base64 (usa Kaleido)."""
    png_bytes = pio.to_image(fig, format="png", scale=scale, engine="kaleido")
    return base64.b64encode(png_bytes).decode("utf-8")


def _fmt_indice(x) -> str:
    if x is None:
        return ""
    try:
        d = x if isinstance(x, Decimal) else Decimal(str(x))
    except Exception:
        return ""
    q = d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    s = f"{q:,.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def build_filas_detalle(periodo_desde: str,
                        periodo_hasta: str,
                        serie_montos,
                        indices_docentes=None,
                        formato_periodo: str = "%b %Y"):
    """
    Devuelve lista de dicts:
    [{"periodo": "Mar 2025", "haber_fmt": "$123.456,78", "indice_fmt": "1,0123"(opc)}, ...]
    """
    meses = _meses_desde_hasta(periodo_desde, periodo_hasta)
    n = min(
        len(meses), len(serie_montos),
        len(indices_docentes)
        if indices_docentes is not None else len(serie_montos))

    filas = []
    for i in range(n):
        fila = {
            "periodo": mes_anio_es(meses[i], abreviado=True),
            "haber_fmt": _fmt_pesos_ar(serie_montos[i]),
        }
        if indices_docentes is not None:
            fila["indice_fmt"] = _fmt_indice(indices_docentes[i])
        filas.append(fila)
    return filas


def _fmt_pesos_ar(x) -> str:
    try:
        d = x if isinstance(x, Decimal) else Decimal(str(x))
    except Exception:
        d = Decimal("0")
    q = d.quantize(Decimal("0.01"))
    s = f"{q:,.2f}"
    return "$" + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(p) -> str:
    if p is None:
        return "-"
    return f"{p*100:.2f}%".replace(".", ",")


def _meses_desde_hasta(periodo_desde: str, periodo_hasta: str):
    from dateutil.relativedelta import relativedelta
    fi = datetime.strptime(periodo_desde, "%Y-%m-%d").date()
    ff = datetime.strptime(periodo_hasta, "%Y-%m-%d").date()
    cur = fi.replace(day=1) + relativedelta(months=1)
    end = ff.replace(day=1)
    meses = []
    while cur <= end:
        meses.append(cur)
        cur += relativedelta(months=1)
    return meses


from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go

def grafico_linea_haber_docente(fecha_inicio: str,
                                fecha_fin: str,
                                monto_inicial,
                                titulo: str = "Haber con aumentos docentes"):
    # 1) Serie calculada (valores por mes)
    serie = calcular_serie_docente(fecha_inicio, fecha_fin, monto_inicial)

    # 2) Fechas mensuales (x)
    fi_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    ff_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    start_dt = fi_dt.replace(day=1) + relativedelta(months=1)  # mes siguiente
    end_dt   = ff_dt.replace(day=1)                            # mes de fecha_fin

    fechas = []
    cur = start_dt
    while cur <= end_dt:
        fechas.append(cur)
        cur += relativedelta(months=1)

    # 3) Alinear por si acaso
    n = min(len(serie), len(fechas))
    serie  = serie[:n]
    fechas = fechas[:n]

    # 4) Convertir a floats para plotly + hover ARS
    def _to_two_dec(x):
        d = x if isinstance(x, Decimal) else Decimal(str(x))
        return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    y_vals = [_to_two_dec(v) for v in serie]

    def _formato_pesos_ar(x: Decimal) -> str:
        q = x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        s = f"{q:,.2f}"  # 1,234.56
        return "$" + s.replace(",", "X").replace(".", ",").replace("X", ".")

    hover_dinero = [_formato_pesos_ar(Decimal(str(v))) for v in y_vals]

    # --- Etiquetas en español ---
    meses_abbr = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    def mes_es(d): return f"{meses_abbr[d.month-1]} {d.year}"

    # === Mostrar SOLO marzo (3) y diciembre (12) ===
    tickvals = [d for d in fechas if d.month in (3, 12)]
    # opcional: asegurá que la última fecha aparezca aunque no sea mar/dic
    if fechas and fechas[-1] not in tickvals:
        tickvals.append(fechas[-1])
    ticktext = [mes_es(d) for d in tickvals]

    # 5) Figura
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=fechas,
            y=y_vals,
            mode="lines+markers",
            name="Haber",
            text=[mes_es(d) for d in fechas],  # hover en español
            customdata=hover_dinero,
            hovertemplate="<b>%{text}</b><br>Haber: %{customdata}<extra></extra>",
            marker=dict(size=5),
            line=dict(width=2),
        )
    )

    fig.update_layout(
        title=titulo,
        xaxis_title="Mes",
        yaxis_title="Monto",
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=60, r=20, t=60, b=60),
        height=450,
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=-45,
        automargin=True,
        showgrid=False,
    )
    fig.update_yaxes(
        separatethousands=True,
        tickprefix="$",
        tickformat=",.2f",
        gridcolor="rgba(0,0,0,0.08)",
        rangemode="tozero",
    )
    return fig





def calcular_serie_docente(fecha_inicio: str, fecha_fin: str,
                           monto_inicial) -> list:
    """
    Calcula la serie de montos multiplicando mes a mes por `indices_docentes`
    desde el PRIMER DÍA DEL MES SIGUIENTE a `fecha_inicio` hasta el mes de `fecha_fin` (inclusive).

    NOTA: `indices_docentes` es DOUBLE en BD. Para evitar errores de precisión binaria
    al multiplicar dinero, se convierte cada índice a Decimal usando `Decimal(str(indice))`.

    Retorna una lista con los montos acumulados (Decimal) por cada mes del rango.
    Además, imprime por consola la fecha (columna `fechas`) y el índice de cada mes procesado.
    """
    # Parseo y normalización de límites
    fi_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    ff_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

    # Regla: siempre se comienza el mes siguiente al de la fecha de inicio
    start_dt = fi_dt.replace(day=1) + relativedelta(months=1)
    end_dt = ff_dt.replace(day=1)

    print(f"Rango a calcular → desde: {start_dt} hasta: {end_dt}")

    if start_dt > end_dt:
        print("⚠️ start_dt > end_dt: no hay meses a procesar en el rango.")
        return []  # No hay meses a procesar

    # Reflejar la tabla para evitar depender de un modelo ORM
    metadata = MetaData()
    movilidad_docente = Table("movilidad_docente",
                              metadata,
                              autoload_with=engine)

    # Traer los meses en el rango [start_dt, end_dt]
    with engine.connect() as conn:
        stmt = (select(movilidad_docente.c.fechas,
                       movilidad_docente.c.indices_docentes).where(
                           and_(
                               movilidad_docente.c.fechas >= start_dt,
                               movilidad_docente.c.fechas <= end_dt,
                           )).order_by(asc(movilidad_docente.c.fechas)))
        rows = conn.execute(stmt).all()

    if not rows:
        print(
            "⚠️ No se encontraron filas en 'movilidad_docente' para el rango solicitado."
        )

    monto = Decimal(str(monto_inicial))
    lista_montos = []

    for fecha, indice in rows:
        # Log de control: fecha e índice del mes
        print(f"Mes: {fecha:%Y-%m-%d} | índice_docente={indice}")

        # `indice` viene como float (DOUBLE en BD). Convertimos vía str → Decimal.
        try:
            idx_dec = Decimal(str(indice))
        except (InvalidOperation, TypeError):
            # Si el índice viene null o inválido, usamos 1 para no alterar el monto
            print("  → índice inválido/null, usando 1.0")
            idx_dec = Decimal('1')
        monto *= idx_dec
        lista_montos.append(monto)

    return lista_montos


def _formato_pesos_ar(x: Decimal) -> str:
    q = x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{q:,.2f}"  # 1,234.56
    return "$" + s.replace(",", "X").replace(".", ",").replace("X", ".")


class CalculadorMovilidadDocente:

    def __init__(
            self,
            nombre_docente,
            cuil_expediente_tipo,
            numero_identificacion,
            cargo_docente,
            periodo_desde,  # 'YYYY-MM-DD'
            periodo_hasta,  # 'YYYY-MM-DD'
            monto,  # str/Decimal/float
            antiguedad_docente,  # opcional
            nivel_educativo,
            situacion_revista,
            establecimiento,
            localidad):
        # Datos del docente
        self.nombre_docente = nombre_docente
        self.cuil_expediente_tipo = cuil_expediente_tipo
        self.numero_identificacion = numero_identificacion
        self.cargo_docente = cargo_docente

        # Períodos
        self.periodo_desde = periodo_desde
        self.periodo_hasta = periodo_hasta

        # Económicos
        self.monto = monto
        self.antiguedad_docente = antiguedad_docente

        # Info adicional
        self.nivel_educativo = nivel_educativo
        self.situacion_revista = situacion_revista
        self.establecimiento = establecimiento
        self.localidad = localidad

        # Resultados
        self.serie_montos = calcular_serie_docente(
            fecha_inicio=self.periodo_desde,
            fecha_fin=self.periodo_hasta,
            monto_inicial=self.monto)
        self.monto_final = self.serie_montos[-1] if self.serie_montos else None

        # Gráfico (Plotly Figure)
        titulo = f"Evolución del haber docente — {self.nombre_docente}" if self.nombre_docente else "Evolución del haber docente"
        self.figura = grafico_linea_haber_docente(
            fecha_inicio=self.periodo_desde,
            fecha_fin=self.periodo_hasta,
            monto_inicial=self.monto,
            titulo=titulo)

    def generar_pdf(self):
        # --- 1) Datos base y métricas de resumen ---
        monto_inicial = self.monto if self.monto is not None else Decimal("0")
        monto_final = self.monto_final if self.monto_final is not None else Decimal(
            "0")

        meses = _meses_desde_hasta(self.periodo_desde, self.periodo_hasta)
        n = min(len(self.serie_montos or []), len(meses))

        variacion_abs = (monto_final -
                         monto_inicial) if n > 0 else Decimal("0")
        variacion_pct = ((monto_final / monto_inicial) -
                         1) if (n > 0 and monto_inicial > 0) else None
        # CAGR mensual
        if n > 0 and monto_inicial > 0 and float(monto_final) > 0:
            promedio_mensual_pct = (float(monto_final) /
                                    float(monto_inicial))**(1.0 / n) - 1.0
        else:
            promedio_mensual_pct = None

        # Mín/Máx mensual
        if n > 0:
            vals = self.serie_montos[:n]
            vmin = min(vals)
            vmax = max(vals)
            imin = vals.index(vmin)
            imax = vals.index(vmax)
            min_mensual_fmt = _fmt_pesos_ar(vmin)
            max_mensual_fmt = _fmt_pesos_ar(vmax)
            min_mensual_periodo = meses[imin].strftime("%b %Y")
            max_mensual_periodo = meses[imax].strftime("%b %Y")
        else:
            min_mensual_fmt = max_mensual_fmt = "-"
            min_mensual_periodo = max_mensual_periodo = "-"

        # --- 2) Gráfico base64 y detalle mensual ---
        try:
            grafico_b64 = fig_to_base64_png(self.figura)
        except Exception:
            grafico_b64 = ""  # evita romper si kaleido no está disponible

        indices_mes = obtener_indices_docentes(self.periodo_desde, self.periodo_hasta)

        filas_detalle = build_filas_detalle(
            periodo_desde=self.periodo_desde,
            periodo_hasta=self.periodo_hasta,
            serie_montos=self.serie_montos or [],
            indices_docentes=indices_mes,  # <-- ahora sí
        )


        # --- 3) Contexto para la plantilla ---
        contexto = {
            # Identificación / cabecera
            "nombre_docente": self.nombre_docente,
            "cuil_expediente_tipo": self.cuil_expediente_tipo,
            "numero_identificacion": self.numero_identificacion,
            "cargo_docente": self.cargo_docente,
            "nivel_educativo": self.nivel_educativo,
            "situacion_revista": self.situacion_revista,
            "establecimiento": self.establecimiento,
            "localidad": self.localidad,

            # Períodos
            "periodo_desde": self.periodo_desde,
            "periodo_hasta": self.periodo_hasta,
            "periodo_desde_fmt": _fmt_ddmmyyyy(self.periodo_desde),  # <-- NUEVO
            "periodo_hasta_fmt": _fmt_ddmmyyyy(self.periodo_hasta),  # <-- NUEVO
            "fecha_emision": datetime.now().strftime("%d/%m/%Y"),

            # Montos (formateados)
            "monto_inicial_fmt": _fmt_pesos_ar(monto_inicial),
            "monto_final_fmt": _fmt_pesos_ar(monto_final),
            "variacion_abs_fmt": _fmt_pesos_ar(variacion_abs),
            "variacion_pct_fmt": _fmt_pct(variacion_pct),
            "meses_calculados": n,
            "promedio_mensual_pct_fmt": _fmt_pct(promedio_mensual_pct),
            "min_mensual_fmt": min_mensual_fmt,
            "min_mensual_periodo": min_mensual_periodo,
            "max_mensual_fmt": max_mensual_fmt,
            "max_mensual_periodo": max_mensual_periodo,

            # Detalle y gráfico
            "grafico_linea_docente": grafico_b64,
            "filas_detalle": filas_detalle,
            "mostrar_indice": True,  # ponelo True si pasás indices_docentes en build_filas_detalle
            "notas": None,  # o lista de strings si querés mostrar notas
        }

        # Si tenés antigüedad, agregala
        if getattr(self, "antiguedad_docente", None):
            contexto["antiguedad_docente"] = self.antiguedad_docente

        # --- 4) Render y PDF (xhtml2pdf como en tu ejemplo) ---
        html_rendered = render_template(
            "calculadora_docente/resultado_calculadora_docente.html",  # ruta de la plantilla
            **contexto)

        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_rendered, dest=pdf_buffer)
        if pisa_status.err:
            return "Error al crear el PDF", 500

        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=
            f"resultado_haber_docente_{self.numero_identificacion or 'docente'}.pdf",
            mimetype="application/pdf")
