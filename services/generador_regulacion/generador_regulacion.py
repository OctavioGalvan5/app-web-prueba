from flask import send_file
from docxtpl import DocxTemplate
from services.calculadora_uma.generador_pdf import obtener_acordada, obtener_valor_uma
from services.calculos import formatear_dinero, transformar_fecha
class Regulacion:
  def __init__(self, datos):
      ### planilla ###
      datos["monto_total_planilla"] = formatear_dinero(float(datos["monto_interes_planilla"]) + float(datos["monto_aprobacion_planilla"]))
      datos["valor_uma_fecha_aprobacion_planilla"] = formatear_dinero(obtener_valor_uma(datos["fecha_aprobacion_planilla"]))
      datos["acordada_fecha_aprobacion_planilla"] = obtener_acordada(datos["fecha_aprobacion_planilla"])
      datos["monto_uma_planilla"] = round((float(datos["monto_interes_planilla"]) + float(datos["monto_aprobacion_planilla"])) / float(obtener_valor_uma(datos["fecha_aprobacion_planilla"])),2)
      ### sentencia trance ###
      datos["monto_total_planilla_trance"] = formatear_dinero(float(datos["monto_interes_planilla_trance"]) + float(datos["monto_aprobacion_planilla"]))
      datos["valor_uma_fecha_pago_planilla"] = formatear_dinero(obtener_valor_uma(datos["fecha_pago_planilla"]))
      datos["acordada_fecha_pago_planilla"] = obtener_acordada(datos["fecha_pago_planilla"])
      datos["monto_uma_planilla_trance"] = round((float(datos["monto_interes_planilla_trance"]) + float(datos["monto_aprobacion_planilla"])) / float(obtener_valor_uma(datos["fecha_pago_planilla"])),2)
      ### planilla ampliacion ###
      datos["monto_total"] = formatear_dinero(float(datos["monto_interes"]) + float(datos["monto_ampliacion"]))
      datos["valor_uma_fecha_aprobacion_planilla_ampliacion"] = formatear_dinero(obtener_valor_uma(datos["fecha_aprobacion_planilla_ampliacion"]))
      datos["acordada_fecha_aprobacion_planilla_ampliacion"] = obtener_acordada(datos["fecha_aprobacion_planilla_ampliacion"])
      datos["monto_uma"] = round((float(datos["monto_interes"]) + float(datos["monto_ampliacion"])) / float(obtener_valor_uma(datos["fecha_aprobacion_planilla_ampliacion"])),2)
      ### sentencia trance ampliacion ###
      datos["monto_total_trance"] = formatear_dinero(float(datos["monto_interes_trance"]) + float(datos["monto_ampliacion"]))
      datos["valor_uma_fecha_pago"] = formatear_dinero(obtener_valor_uma(datos["fecha_pago"]))
      datos["acordada_fecha_pago"] = obtener_acordada(datos["fecha_pago"])
      datos["monto_uma_trance"] = round((float(datos["monto_interes_trance"]) + float(datos["monto_ampliacion"])) / float(obtener_valor_uma(datos["fecha_pago"])),2)

      ### planilla ampliacion 2 ###
      datos["monto_total_2"] = formatear_dinero(float(datos["monto_interes_2"]) + float(datos["monto_ampliacion_2"]))
      datos["valor_uma_fecha_aprobacion_planilla_ampliacion_2"] = formatear_dinero(obtener_valor_uma(datos["fecha_aprobacion_planilla_ampliacion_2"]))
      datos["acordada_fecha_aprobacion_planilla_ampliacion_2"] = obtener_acordada(datos["fecha_aprobacion_planilla_ampliacion_2"])
      datos["monto_uma_2"] = round((float(datos["monto_interes_2"]) + float(datos["monto_ampliacion_2"])) / float(obtener_valor_uma(datos["fecha_aprobacion_planilla_ampliacion_2"])),2)

      ### sentencia trance ampliacion 2 ###
      datos["monto_total_trance_2"] = formatear_dinero(float(datos["monto_interes_trance_2"]) + float(datos["monto_ampliacion_2"]))
      datos["valor_uma_fecha_pago_2"] = formatear_dinero(obtener_valor_uma(datos["fecha_pago_2"]))
      datos["acordada_fecha_pago_2"] = obtener_acordada(datos["fecha_pago_2"])
      datos["monto_uma_trance_2"] = round((float(datos["monto_interes_trance_2"]) + float(datos["monto_ampliacion_2"])) / float(obtener_valor_uma(datos["fecha_pago_2"])),2)


      ### planilla ampliacion 3 ###
      datos["monto_total_3"] = formatear_dinero(float(datos["monto_interes_3"]) + float(datos["monto_ampliacion_3"]))
      datos["valor_uma_fecha_aprobacion_planilla_ampliacion_3"] = formatear_dinero(obtener_valor_uma(datos["fecha_aprobacion_planilla_ampliacion_3"]))
      datos["acordada_fecha_aprobacion_planilla_ampliacion_3"] = obtener_acordada(datos["fecha_aprobacion_planilla_ampliacion_3"])
      datos["monto_uma_3"] = round((float(datos["monto_interes_3"]) + float(datos["monto_ampliacion_3"])) / float(obtener_valor_uma(datos["fecha_aprobacion_planilla_ampliacion_3"])),2)

        ### sentencia trance ampliacion 2 ###
      datos["monto_total_trance_3"] = formatear_dinero(float(datos["monto_interes_trance_3"]) + float(datos["monto_ampliacion_3"]))
      datos["valor_uma_fecha_pago_3"] = formatear_dinero(obtener_valor_uma(datos["fecha_pago_3"]))
      datos["acordada_fecha_pago_3"] = obtener_acordada(datos["fecha_pago_3"])
      datos["monto_uma_trance_3"] = round((float(datos["monto_interes_trance_3"]) + float(datos["monto_ampliacion_3"])) / float(obtener_valor_uma(datos["fecha_pago_3"])),2)



      ### planilla ###
      datos["fecha_aprobacion_planilla"] = transformar_fecha(datos["fecha_aprobacion_planilla"])
      datos["monto_aprobacion_planilla"] = formatear_dinero(datos["monto_aprobacion_planilla"])
      datos["fecha_comienzo_planilla"] = transformar_fecha(datos["fecha_comienzo_planilla"])
      datos["fecha_corte_planilla"] = transformar_fecha(datos["fecha_corte_planilla"])
      datos["monto_interes_planilla"] = formatear_dinero(datos["monto_interes_planilla"])
      datos["sentencia_interlocutoria_costas"] = transformar_fecha(datos["sentencia_interlocutoria_costas"])
      datos["fecha_sentencia_apelacion"] = transformar_fecha(datos["fecha_sentencia_apelacion"])

       ## sentencia trance liquidacion
      datos["fecha_sentencia_trance_liquidacion"] = transformar_fecha(datos["fecha_sentencia_trance_liquidacion"])
      datos["fecha_pago_planilla" ] = transformar_fecha(datos["fecha_pago_planilla"])
      datos["monto_interes_planilla_trance"] = formatear_dinero(datos["monto_interes_planilla_trance"])

      ## planilla ampliacion
      datos["fecha_aprobacion_planilla_ampliacion"] = transformar_fecha(datos["fecha_aprobacion_planilla_ampliacion"])
      datos["monto_ampliacion"] = formatear_dinero(datos["monto_ampliacion"])
      datos["fecha_inicio"] = transformar_fecha(datos["fecha_inicio"])
      datos["fecha_corte"] = transformar_fecha(datos["fecha_corte"])
      datos["monto_interes"] = formatear_dinero(datos["monto_interes"])
      datos["fecha_sentencia_interlocutoria"] = transformar_fecha(datos["fecha_sentencia_interlocutoria"])

      ## sentencia trance planilla ampliacion 

      datos["sentencia_trance_fecha"] = transformar_fecha(datos["sentencia_trance_fecha"])
      datos["fecha_pago"] = transformar_fecha(datos["fecha_pago"])
      datos["monto_interes_trance"] = formatear_dinero(datos["monto_interes_trance"])

      ## planilla ampliacion 2
      datos["fecha_aprobacion_planilla_ampliacion_2"] = transformar_fecha(datos["fecha_aprobacion_planilla_ampliacion_2"])
      datos["monto_ampliacion_2"] = formatear_dinero(datos["monto_ampliacion_2"])
      datos["fecha_inicio_2"] = transformar_fecha(datos["fecha_inicio_2"])
      datos["fecha_corte_2"] = transformar_fecha(datos["fecha_corte_2"])
      datos["monto_interes_2"] = formatear_dinero(datos["monto_interes_2"])
      datos["fecha_sentencia_interlocutoria_2"] = transformar_fecha(datos["fecha_sentencia_interlocutoria_2"])

      ## sentencia trance planilla ampliacion 2
      datos["sentencia_trance_fecha_2"] = transformar_fecha(datos["sentencia_trance_fecha_2"])
      datos["fecha_pago_2"] = transformar_fecha(datos["fecha_pago_2"])
      datos["monto_interes_trance_2"] = formatear_dinero(datos["monto_interes_trance_2"])

      ## planilla ampliacion 3
      datos["fecha_aprobacion_planilla_ampliacion_3"] = transformar_fecha(datos["fecha_aprobacion_planilla_ampliacion_3"])
      datos["monto_ampliacion_3"] = formatear_dinero(datos["monto_ampliacion_3"])
      datos["fecha_inicio_3"] = transformar_fecha(datos["fecha_inicio_3"])
      datos["fecha_corte_3"] = transformar_fecha(datos["fecha_corte_3"])
      datos["monto_interes_3"] = formatear_dinero(datos["monto_interes_3"])
      datos["fecha_sentencia_interlocutoria_3"] = transformar_fecha(datos["fecha_sentencia_interlocutoria_3"])

      ## sentencia trance planilla ampliacion 3
      datos["sentencia_trance_fecha_3"] = transformar_fecha(datos["sentencia_trance_fecha_3"])
      datos["fecha_pago_3"] = transformar_fecha(datos["fecha_pago_3"])
      datos["monto_interes_trance_3"] = formatear_dinero(datos["monto_interes_trance_3"])


      self.datos = datos

  def crear_documento(self):
      plantilla_path = "datos/regulacion/plantilla_regulacion.docx"
      output_path = "datos/regulacion/regulacion_final.docx"
      doc = DocxTemplate(plantilla_path)

      # Renderizar el documento con los datos
      doc.render(self.datos)

      # Guardar el documento renderizado
      doc.save(output_path)

      # Enviar el archivo para su descarga
      return send_file(output_path, as_attachment=True)