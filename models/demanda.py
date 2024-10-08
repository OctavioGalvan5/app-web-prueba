from docxtpl import DocxTemplate
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches
import os
import tempfile
from flask import request, send_file
from werkzeug.utils import secure_filename


class Formulario:
    def __init__(self, datos):
        """Inicializa la clase con el diccionario de datos del formulario."""
        self.datos = datos

    def datos_cliente(self):
        """Recoge los datos del cliente."""
        return {
            'genero': self.datos["datos_cliente"].get('genero'),
            'nombre': self.datos["datos_cliente"].get('nombre'),
            'dni': self.datos["datos_cliente"].get('dni'),
            'domicilio': self.datos["datos_cliente"].get('domicilio'),
            'localidad': self.datos["datos_cliente"].get('localidad'),
            "fecha_adquisicion_derecho": self.datos["datos_cliente"].get("fecha_adquisicion_derecho"),
            "garciaVidal" : self.datos["datos_cliente"].get("garciaVidal")
        }

    def beneficio(self):
        """Recoge los datos de beneficios."""
        return {
            'fecha_reajuste': self.datos["beneficio"].get('fecha_reajuste'),
            'expediente_reajuste': self.datos["beneficio"].get('expediente_reajuste'),
            'numero_beneficio': self.datos["beneficio"].get('numero_beneficio'),
            'fecha_inicio_remuneraciones': self.datos["beneficio"].get('fecha_inicio_remuneraciones'),
            'fecha_fin_remuneraciones': self.datos["beneficio"].get('fecha_fin_remuneraciones'),
            'fecha_cese': self.datos["beneficio"].get('fecha_cese'),
            'ultima_remuneracion_actividad': self.datos["beneficio"].get('ultima_remuneracion_actividad'),
            'fecha_ultima_remuneracion_actividad': self.datos["beneficio"].get('fecha_ultima_remuneracion_actividad'),
            'ultima_remuneracion_actualizada_anses': self.datos["beneficio"].get('ultima_remuneracion_actualizada_anses'),
            'fecha_alta_primer_haber': self.datos["beneficio"].get('fecha_alta_primer_haber'),
            'monto_primer_haber': self.datos["beneficio"].get('monto_primer_haber'),
            'taza_de_reemplazo': self.datos["beneficio"].get('taza_de_reemplazo'),
        }

    def servicios(self):
        """Recoge los datos de servicios."""
        # Inicializar los textos de servicios
        servicios_dependencia = ""
        servicios_autonomos = ""

        # Comprobar si se deben incluir servicios en dependencia
        if self.datos["servicios"].get('servicios_dependencia'):
            servicios_dependencia = "Cargo desempeñado y empleador al cese: " + \
                self.datos["servicios_dependencia"].get('cargo_desempleado', "") + " en " + \
                self.datos["servicios_dependencia"].get('empleador', "")

        # Comprobar si se deben incluir servicios autónomos
        if self.datos["servicios"].get('servicios_autonomos'):
            servicios_autonomos = "Servicios Autónomos: " + \
                self.datos["servicios_autonomos"].get('autonomo_input1', "") + " en " + \
                self.datos["servicios_autonomos"].get('autonomo_input2', "")

        # Devolver un diccionario con los resultados
        return {
            'servicios_dependencia': servicios_dependencia,
            'servicios_autonomos': servicios_autonomos,
        }

    def sumas_no_remunerativas(self):
        """Recoge los datos de servicios."""
        # Inicializar los textos de servicios
        Titulo_sumas_no_remunerativas = ""
        parrafo_introduccion = ""
        parrafo_sumas=""
        parrafo_legalidad = ""


        if self.datos["casillas_verificacion"].get('opcion_sumas_remunerativas', False):
            # Título de la sección de sumas no remunerativas
            Titulo_sumas_no_remunerativas = "De las sumas no remunerativas"

            parrafo_introduccion = (
                "Solicito se incorporen para el cálculo del ingreso base las sumas no remunerativas percibidas por mi mandante "
                "con carácter de normal y habitual por parte de su empleadora, provincia de Salta, conforme a la doctrina sentada "
                "en el caso 'Rainone de Ruffo' de la CSJN. Se acompaña a la presente la historia laboral de mi mandante, "
                "en donde se observa una columna que dice 'remuneración total', que es lo liquidado de mi mandante (incluye las "
                "sumas no remunerativas) y una que dice 'remuneración', que es sobre lo que aportó su empleador, ocasionándole "
                "un perjuicio a mi mandante."
            )

            # Párrafo de legalidad
            parrafo_legalidad = (
                "La Corte Suprema de Justicia de la Nación reconoció que el monto de las sumas no remunerativas debe "
                "ser considerado por ANSES para el cómputo del beneficio. Así, en la causa 'Rainone de Ruffo, Juana Teresa "
                "Berta c/ ANSeS s/ reajustes varios', Sentencia del 02.03.2011, donde se trataba de sumas no remunerativas "
                "abonadas por el propio ANSES como empleador, el Tribunal sostuvo que correspondía '(...) admitir la pretensión "
                "de la recurrente y ordenar que dichos montos sean incorporados en el cálculo del haber inicial ordenado por el "
                "juez de primera instancia, sin perjuicio del cargo por aportes omitidos y de las contribuciones que deban "
                "realizarse con destino a la seguridad social'. Máxime cuando el propio Organismo había reconocido como "
                "'remuneraciones sin aporte' las sumas en cuestión."
            )

            # Añadir el resto de los argumentos
            parrafo_legalidad += (
                " En consecuencia, al tratarse de sumas no remunerativas percibidas con carácter normal y habitual, corresponde "
                "considerar su monto para el cálculo de la jubilación, fundamentando que la misma ley de jubilaciones indica en "
                "su artículo 6 que 'a los fines previsionales, remuneración es todo ingreso que recibe un trabajador en retribución "
                "o compensación por su actividad personal prestados en relación de dependencia, incluidos los suplementos que "
                "tengan el carácter de habituales y regulares'."
            )

            parrafo_legalidad += (
                " Los pagos se hicieron con regularidad (variando el porcentaje respecto del salario). La omisión de aportes y "
                "contribuciones, por el eventual incumplimiento de los deberes a cargo de la Administración como agente de "
                "retención, no puede cambiar la verdadera naturaleza del desembolso efectuado. Además, la liberación de todo cargo "
                "al Estado Nacional en la implementación de los incentivos se refiere al origen de los fondos para llevar adelante "
                "el programa (arts. 4, 5 y 11 de la ley 23283), pero no lo libera de otras obligaciones, entre las que se encuentran "
                "las de obrar como agente de retención de los aportes y realizar las cotizaciones de seguridad social."
            )

            parrafo_legalidad += (
                " Más aún, el carácter remunerativo de los conceptos abonados encuadra en el art. 6 de la ley 24241, que asigna esa "
                "naturaleza 'a ciertas sumas que son abonadas a agentes de la Administración Pública, entre las que menciona al "
                "'premio estímulo, gratificaciones u otros conceptos de análogas características', con la modalidad de poner a cargo "
                "del agente, además de su aporte personal, la contribución que corresponde al empleador."
            )

            parrafo_legalidad += (
                " En virtud de lo expuesto, solicito se incorporen al cómputo del haber jubilatorio de mi mandante las sumas percibidas "
                "como no remunerativas y se ordene a su empleadora realizar las contribuciones previsionales correspondientes, teniendo "
                "en cuenta el criterio de ambas salas sobre este tema: Van Cauwlaert, Eduardo, sent. del 9/6/17, haciendo mérito de la "
                "doctrina que emana del precedente 'Rainone de Ruffo, Juana Teresa Berta' (Fallos: 334:210), y Fallos: 333:699 "
                "'González, Martín Nicolás c/ Polimat S.A. y otro', sent. del 19/5/2010."
            )

        # Comprobar si se deben incluir servicios en dependencia
        if self.datos["sumas_no_remunerativas"]["recibos"]["Recibos_Si"]:
            parrafo_sumas = "Se adjunta equiparación de haberes, de la que surge que el cargo desempeñado por mi representado al cese fue de " + self.datos["sumas_no_remunerativas"]["recibos_si"]["Cargo_Desempeñado"] + " en " + self.datos["sumas_no_remunerativas"]["recibos_si"]["Lugar_Desempeñado"] + ", con una antigüedad de " + self.datos["sumas_no_remunerativas"]["recibos_si"]["Años_antiguedad"] + " años de servicios.Asimismo, se adjuntan recibos de sueldo, de los que surgen que el empleador abonó a mi representado, haberes sin aportes bajo los siguientes códigos y conceptos, los que no fueron considerados para el cálculo del haber inicial"

        # Comprobar si se deben incluir servicios autónomos
        if self.datos["sumas_no_remunerativas"]["recibos"]["Recibos_No"]:
           parrafo_sumas = "Asimismo, peticiono se libre oficio a " + self.datos["sumas_no_remunerativas"]["recibos_no"]["Librar_oficio_a"] + " a los fines de que remita los recibos de sueldo de mi representada que se encuentran en su poder, correspondientes al período " + self.datos["sumas_no_remunerativas"]["recibos_no"]["inicio_periodo_sumas"] + " hasta " + self.datos["sumas_no_remunerativas"]["recibos_no"]["fin_periodo_sumas"] + " , de los que surgirán las sumas abonadas como no remunerativas, En su defecto, peticiono informe los haberes con aportes y sin aportes abonados en cada período peticionado.  De ellos surgirán las sumas no remunerativas abonadas por el empleador, bajo los siguientes códigos y conceptos: "

        if self.datos["sumas_no_remunerativas"]["Imagen"]["Imagen"]:
            parrafo_sumas += "\nImagen aquí"

        # Devolver un diccionario con los resultados
        return {
            'parrafo_sumas': parrafo_sumas,
            'parrafo_legalidad': parrafo_legalidad,
            'Titulo_sumas_no_remunerativas' : Titulo_sumas_no_remunerativas,
            'parrafo_introduccion': parrafo_introduccion
        }

    def generar_diccionario_docx(self):
        """Genera el diccionario que se usará para crear el archivo Word."""
        doc_data = {
            'cliente': self.datos_cliente(),
            'beneficios': self.beneficio(),
            'servicios': self.servicios(),
            'sumas_no_remunerativas': self.sumas_no_remunerativas()
            # Agrega más secciones según lo necesites
        }
        return doc_data

    def crear_archivo_word(self):
        """Crea un archivo Word usando la plantilla y los datos proporcionados."""
        fecha_escrito = self.datos["datos_cliente"].get("fecha_adquisicion_derecho")
        fecha_escrito = datetime.strptime(fecha_escrito, '%Y-%m-%d')

        # Restar un año si garcia_vidal es True
        if self.datos["datos_cliente"].get("garciaVidal"):
            fecha_escrito = fecha_escrito - timedelta(days=365)  # Restar un año

        # Seleccionar plantilla según la fecha_escrito
        if fecha_escrito < datetime(2018, 3, 1):
            plantilla = 'datos/MODELO ANT 03.2018. COMPLETO..docx'
        elif datetime(2018, 3, 1) <= fecha_escrito < datetime(2021, 1, 1):
            plantilla = 'datos/plantillaB.docx'
        else:
            plantilla = 'datos/plantillaC.docx'

        # Cargar la plantilla y crear el contexto
        doc = DocxTemplate(plantilla)
        contexto = {
            'datos_cliente': self.datos_cliente(),  # Método para los datos del cliente
            'servicios': self.servicios(),           # Método para los datos de servicios
            'beneficio': self.beneficio(),           # Método para los datos de beneficio
            'sumas_no_remunerativas': self.sumas_no_remunerativas()  # Método para las sumas no remunerativas
        }

        # Renderizar el documento con el contexto
        doc.render(contexto)

        # Guardar el documento editado temporalmente
        final_path = 'datos/documento_editado.docx'
        doc.save(final_path)

        # Devolver la ruta del archivo
        return final_path

    def procesar_documento(self):
        # Crear el archivo Word
        documento_path = self.crear_archivo_word()  # Obtiene la ruta del documento generado

        # Devolver el archivo al usuario
        return send_file(documento_path, as_attachment=True)