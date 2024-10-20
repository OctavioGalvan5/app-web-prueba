from datetime import datetime
from sqlalchemy import text
from babel.numbers import format_currency
from io import BytesIO
from flask import render_template, send_file
from xhtml2pdf import pisa
from services.calculos import convertir_fecha


class calculadora_movilidad:
    def __init__(self, engine):
        self.engine = engine

    def buscar_fechas(self, fecha_ingresada, monto):
        fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()
        lista_filas = []

        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas <= :fecha ORDER BY fechas DESC LIMIT 1"), {"fecha": fecha_ingresada_dt})
            fila_menor = result.fetchone()

            if fila_menor:
                lista_filas.append(self._calcular_montos(fila_menor, monto))
            else:
                print("No se encontró una fecha menor a la ingresada.")
                return []

            result_mayores = conn.execute(text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas > :fecha ORDER BY fechas ASC"), {"fecha": fecha_ingresada_dt})
            filas_mayores = result_mayores.fetchall()

            if filas_mayores:
                for fila in filas_mayores:
                    lista_filas.append(self._calcular_montos(fila, monto))
            else:
                print("No se encontraron filas con fechas mayores a la ingresada.")
                return []

        return lista_filas

    def _calcular_montos(self, fila, monto):
        # Realiza los cálculos con las columnas y devuelve una tupla con los resultados formateados
        monto_columna2 = fila[2] * monto
        monto_columna3 = fila[3] * monto
        monto_columna4 = fila[4] * monto
        monto_columna5 = fila[5] * monto
        monto_columna6 = fila[6] * monto
        monto_columna7 = fila[7] * monto

        return (
            convertir_fecha(fila[1]),
            MoneyFormatter.formatear_dinero(monto_columna2),
            MoneyFormatter.formatear_dinero(monto_columna3),
            MoneyFormatter.formatear_dinero(monto_columna4),
            MoneyFormatter.formatear_dinero(monto_columna5),
            MoneyFormatter.formatear_dinero(monto_columna6),
            MoneyFormatter.formatear_dinero(monto_columna7),
        )


class generador_pdf_calculadora_movilidad:
    def __init__(self, template, data):
        self.template = template
        self.data = data

    def generate_pdf(self):
        rendered = render_template(self.template, **self.data)

        # Crear el PDF en memoria
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)

        if pisa_status.err:
            raise Exception("Error al crear el PDF")

        pdf_buffer.seek(0)
        return pdf_buffer

    def send_pdf(self, pdf_buffer, filename='resultado.pdf'):
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
        
class MoneyFormatter:
    @staticmethod
    def formatear_dinero(cantidad):
        return format_currency(cantidad, 'ARS', locale='es_AR').replace(u'\xa0', u'')