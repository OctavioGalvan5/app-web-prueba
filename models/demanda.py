from docxtpl import DocxTemplate
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches
import os
import tempfile
from flask import request, send_file
from werkzeug.utils import secure_filename
from models.calculos import formatear_dinero, transformar_fecha


class Formulario:
    def __init__(self, datos):
        """Inicializa la clase con el diccionario de datos del formulario."""
        self.datos = datos

    def datos_cliente(self):
        """Recoge los datos del cliente."""
        genero = ""
        if self.datos["datos_cliente"].get('genero') == "Masculino":
            genero = "del Sr"
        elif self.datos["datos_cliente"].get('genero') == "Femenino":
            genero = "de la Sra"
        return {
            'genero': genero,
            'nombre': self.datos["datos_cliente"].get('nombre'),
            'dni': self.datos["datos_cliente"].get('dni'),
            'domicilio': self.datos["datos_cliente"].get('domicilio'),
            'localidad': self.datos["datos_cliente"].get('localidad'),
            "fecha_adquisicion_derecho": transformar_fecha(self.datos["datos_cliente"].get("fecha_adquisicion_derecho")),
            "garciaVidal" : self.datos["datos_cliente"].get("garciaVidal")
        }

    def beneficio(self):
        """Recoge los datos de beneficios."""
        return {
            'fecha_reajuste': transformar_fecha(self.datos["beneficio"].get('fecha_reajuste')),
            'expediente_reajuste': self.datos["beneficio"].get('expediente_reajuste'),
            'numero_beneficio': self.datos["beneficio"].get('numero_beneficio'),
            'fecha_inicio_remuneraciones': transformar_fecha(self.datos["beneficio"].get('fecha_inicio_remuneraciones')),
            'fecha_fin_remuneraciones': transformar_fecha(self.datos["beneficio"].get('fecha_fin_remuneraciones')),
            'fecha_cese': transformar_fecha(self.datos["beneficio"].get('fecha_cese')),
            'ultima_remuneracion_actividad': formatear_dinero(self.datos["beneficio"].get('ultima_remuneracion_actividad')),
            'fecha_ultima_remuneracion_actividad': transformar_fecha(self.datos["beneficio"].get('fecha_ultima_remuneracion_actividad')),
            'ultima_remuneracion_actualizada_anses': formatear_dinero(self.datos["beneficio"].get('ultima_remuneracion_actualizada_anses')),
            'fecha_alta_primer_haber': transformar_fecha(self.datos["beneficio"].get('fecha_alta_primer_haber')),
            'monto_primer_haber': formatear_dinero(self.datos["beneficio"].get('monto_primer_haber')),
            'taza_de_reemplazo': self.datos["beneficio"].get('taza_de_reemplazo'),
            'ultimo_haber': formatear_dinero(self.datos["beneficio"].get('ultimo_haber')),
            'fecha_ultimo_haber': transformar_fecha(self.datos["beneficio"].get('fecha_ultimo_haber')),
            'fecha_reclamo' : transformar_fecha(self.datos["beneficio"].get('fecha_reclamo')),
        }

    def servicios(self):
        """Recoge los datos de servicios."""
        # Inicializar los textos de servicios
        servicios_dependencia = "Servicios en Dependencia: No tiene"
        servicios_autonomos = "Servicios Autonomos: No tiene"

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
        parrafo_legalidad1 = ""
        parrafo_legalidad2 = ""
        parrafo_legalidad3 = ""
        parrafo_legalidad4 = ""
        parrafo_legalidad5 = ""


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
            parrafo_legalidad1 = (
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
            parrafo_legalidad2 = (
                " En consecuencia, al tratarse de sumas no remunerativas percibidas con carácter normal y habitual, corresponde "
                "considerar su monto para el cálculo de la jubilación, fundamentando que la misma ley de jubilaciones indica en "
                "su artículo 6 que 'a los fines previsionales, remuneración es todo ingreso que recibe un trabajador en retribución "
                "o compensación por su actividad personal prestados en relación de dependencia, incluidos los suplementos que "
                "tengan el carácter de habituales y regulares'."
            )

            parrafo_legalidad3 = (
                " Los pagos se hicieron con regularidad (variando el porcentaje respecto del salario). La omisión de aportes y "
                "contribuciones, por el eventual incumplimiento de los deberes a cargo de la Administración como agente de "
                "retención, no puede cambiar la verdadera naturaleza del desembolso efectuado. Además, la liberación de todo cargo "
                "al Estado Nacional en la implementación de los incentivos se refiere al origen de los fondos para llevar adelante "
                "el programa (arts. 4, 5 y 11 de la ley 23283), pero no lo libera de otras obligaciones, entre las que se encuentran "
                "las de obrar como agente de retención de los aportes y realizar las cotizaciones de seguridad social."
            )

            parrafo_legalidad4 = (
                " Más aún, el carácter remunerativo de los conceptos abonados encuadra en el art. 6 de la ley 24241, que asigna esa "
                "naturaleza 'a ciertas sumas que son abonadas a agentes de la Administración Pública, entre las que menciona al "
                "'premio estímulo, gratificaciones u otros conceptos de análogas características', con la modalidad de poner a cargo "
                "del agente, además de su aporte personal, la contribución que corresponde al empleador."
            )

            parrafo_legalidad5 = (
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
           parrafo_sumas = "Asimismo, peticiono se libre oficio a " + self.datos["sumas_no_remunerativas"]["recibos_no"]["Librar_oficio_a"] + " a los fines de que remita los recibos de sueldo de mi representada que se encuentran en su poder, correspondientes al período " + transformar_fecha(self.datos["sumas_no_remunerativas"]["recibos_no"]["inicio_periodo_sumas"]) + " hasta " + transformar_fecha(self.datos["sumas_no_remunerativas"]["recibos_no"]["fin_periodo_sumas"]) + " , de los que surgirán las sumas abonadas como no remunerativas, En su defecto, peticiono informe los haberes con aportes y sin aportes abonados en cada período peticionado.  De ellos surgirán las sumas no remunerativas abonadas por el empleador, bajo los siguientes códigos y conceptos: "

        if self.datos["sumas_no_remunerativas"]["Imagen"]["Imagen"]:
            parrafo_sumas += "\nImagen aquí"

        # Devolver un diccionario con los resultados
        return {
            'parrafo_sumas': parrafo_sumas,
            'parrafo_legalidad1': parrafo_legalidad1,
            'parrafo_legalidad2': parrafo_legalidad2,
            'parrafo_legalidad3': parrafo_legalidad3,
            'parrafo_legalidad4': parrafo_legalidad4,
            'parrafo_legalidad5': parrafo_legalidad5,
            'Titulo_sumas_no_remunerativas' : Titulo_sumas_no_remunerativas,
            'parrafo_introduccion': parrafo_introduccion
        }

    def error_material(self):
        """Recoge los datos de servicios."""
        # Inicializar los textos de servicios
        Titulo_error_material = ""
        parrafo_1 = ""
        parrafo_2 =""
        parrafo_3 = ""
        parrafo_4 = ""
        parrafo_5= ""
        parrafo_6= ""
        parrafo_7 = ""


        if self.datos["casillas_verificacion"].get('opcion_error_material', False):
            # Título de la sección de sumas no remunerativas
            Titulo_error_material= "Del error material "

            parrafo_1 = (
                "Mi mandante trabajó en " + self.datos["error_material"]["Lugar_error"] + " desde el " + self.datos["error_material"]["fecha_inicio_remuneraciones_error"] + " hasta el " + self.datos["error_material"]["fecha_fin_remuneraciones_error"] +"."
            )

            # Párrafo de legalidad
            parrafo_2 = (
                "Del detalle de beneficios de Anses se observan los siguientes errores materiales en los que incurrió el organismo previsional al momento del cálculo del haber jubilatorio inicial:"
            )

            # Añadir el resto de los argumentos
            parrafo_3= (
                "Toma remuneraciones erróneas, diferentes a las efectivamente percibidas:"
            )

            parrafo_4 = (
                "Se adjunta cálculo de haber de caja con y sin corrección del error material, de los que surgen los siguientes promedios de remuneraciones:"
            )

            parrafo_5 = (
                "W de caja con error material en remuneraciones consideradas: " + self.datos["error_material"]["W_error"] +"."
            )

            parrafo_6 = (
                "W de caja sin error material, con remuneraciones correctas: " + self.datos["error_material"]["W_sin_error"] +"."
            )
            parrafo_7 = (
                "Solicito se corrija el error material y se tomen las verdaderas remuneraciones percibidas para el cálculo del haber inicial." 
            )

        
        return {
            'Titulo_error_material': Titulo_error_material,
            'parrafo_1': parrafo_1,
            'parrafo_2': parrafo_2,
            'parrafo_3': parrafo_3,
            'parrafo_4': parrafo_4,
            'parrafo_5': parrafo_5,
            'parrafo_6': parrafo_6,
            'parrafo_7': parrafo_7,
        }

    def generar_diccionario_docx(self):
        """Genera el diccionario que se usará para crear el archivo Word."""
        doc_data = {
            'cliente': self.datos_cliente(),
            'beneficio': self.beneficio(),
            'servicios': self.servicios(),
            'sumas_no_remunerativas': self.sumas_no_remunerativas(),
            'error_material': self.error_material()
            # Agrega más secciones según lo necesites
        }
        return doc_data

    def crear_archivo_word(self, imagenes_por_marcador):
        """Crea un archivo Word usando la plantilla y los datos proporcionados, incluyendo imágenes."""

        fecha_escrito = self.datos["datos_cliente"].get("fecha_adquisicion_derecho")
        fecha_escrito = datetime.strptime(fecha_escrito, '%Y-%m-%d')

        # Restar un año si garcia_vidal es True
        if self.datos["datos_cliente"].get("garciaVidal"):
            fecha_escrito = fecha_escrito - timedelta(days=365)

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
            'datos_cliente': self.datos_cliente(),
            'servicios': self.servicios(),
            'beneficio': self.beneficio(),
            'sumas_no_remunerativas': self.sumas_no_remunerativas(),
            'error_material': self.error_material()
        }

        # Renderizar el documento con el contexto
        doc.render(contexto)

        # Guardar el documento editado temporalmente
        temp_doc_path = 'datos/documento_temporal.docx'
        doc.save(temp_doc_path)

        # Manejo de las imágenes
        doc = Document(temp_doc_path)

        # Insertar imágenes en posiciones específicas según el diccionario
        for marcador, imagen_path in imagenes_por_marcador.items():
            for paragraph in doc.paragraphs:
                if marcador in paragraph.text:  # Buscar el marcador
                    paragraph.text = paragraph.text.replace(marcador, '')  # Eliminar el marcador del texto

                    if imagen_path:  # Verificar si hay imagen para ese marcador
                        run = paragraph.add_run()
                        run.add_picture(imagen_path, width=Inches(5))  # Ajusta el tamaño según sea necesario
                    break  # Detener la búsqueda en los párrafos una vez encontrado el marcador

        # Guardar el documento final editado
        final_path = 'datos/documento_editado.docx'
        doc.save(final_path)

        # Devolver la ruta del archivo final
        return final_path

    def procesar_imagenes(self):
        """Procesa las imágenes subidas por el usuario y las asigna a sus respectivos marcadores."""
        # Obtener las imágenes proporcionadas por el usuario (pueden ser opcionales)
        imagen1 = self.datos["sumas_no_remunerativas"]["Imagen"].get("Imagen")  # Primer input de imagen (puede ser None)
        imagen2 = self.datos["error_material"]["Imagen"].get("Imagen")

        # Crear diccionario para asignar las imágenes a sus marcadores
        imagenes_por_marcador = {}

        # Asignar cada imagen a su respectivo marcador si existe
        for imagen, marcador in zip([imagen1, imagen2], ['Imagen_suma_aqui', 'Imagen_error_material_aqui']):
            if imagen:  # Verificar si el usuario subió una imagen
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(imagen.read())
                    imagenes_por_marcador[marcador] = temp_file.name  # Mapea el marcador a la ruta del archivo temporal
            else:
                imagenes_por_marcador[marcador] = None  # No hay imagen para este marcador, se eliminará del documento

        # Llama a la función para crear el documento Word
        documento_path = self.crear_archivo_word(imagenes_por_marcador)  # Pasa el diccionario

        # Eliminar los archivos temporales después de usarlos
        for temp_file_path in imagenes_por_marcador.values():
            if temp_file_path:  # Solo eliminar archivos que existan
                try:
                    os.remove(temp_file_path)
                except FileNotFoundError:
                    print(f"El archivo {temp_file_path} no se encontró y no pudo ser eliminado.")

        # Enviar el archivo generado al usuario como descarga
        return send_file(documento_path, as_attachment=True)