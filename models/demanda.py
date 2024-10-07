from docxtpl import DocxTemplate
from datetime import datetime, timedelta
from flask import send_file

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
        parrafo_sumas=""

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
        }

    def generar_diccionario_docx(self):
        """Genera el diccionario que se usará para crear el archivo Word."""
        doc_data = {
            'cliente': self.datos_cliente(),
            'beneficios': self.beneficio(),
            'servicios': self.servicios(),
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
        # Cargar el archivo .docx de la plantilla seleccionada
        plantilla = 'ruta/a/tu/plantilla.docx'  # Especifica la ruta de tu plantilla
        doc = DocxTemplate(plantilla)

        # Crear el contexto usando los datos del formulario
        contexto = {
            'datos_cliente': self.datos_cliente(),  # Asegúrate de que este método devuelva el formato correcto
            'servicios': self.servicios(),           # Asegúrate de que este método devuelva el formato correcto
            'beneficio': self.beneficio()            # Asegúrate de que este método devuelva el formato correcto
        }

        # Renderizar el documento con el contexto
        doc.render(contexto)

        # Guardar el documento editado temporalmente
        final_path = 'datos/documento_editado.docx'
        doc.save(final_path)

        # Devolver el archivo editado al usuario
        return send_file(final_path, as_attachment=True)