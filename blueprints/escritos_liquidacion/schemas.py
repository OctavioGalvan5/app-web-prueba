"""
Schemas para el módulo de escritos de liquidación.

Define las estructuras de datos (dataclasses) que representan los campos del formulario,
con métodos para parsear desde request.form y convertir al contexto que espera el template docx.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OpcionLiquidacion:
    """Representa una opción de liquidación (1 a 4) con sus datos numéricos."""
    numero: int
    movilidad: str = ""
    capital: str = ""
    intereses: str = ""
    total: str = ""
    tope_9: bool = False

    def to_template_context(self) -> dict:
        """Genera las variables que espera el docx para esta opción."""
        n = self.numero
        ctx = {
            f'movilidad_opcion_{n}': self.movilidad,
            f'capital_opcion_{n}': self.capital,
            f'intereses_opcion_{n}': self.intereses,
            f'total_opcion_{n}': self.total,
            f'tope_9_opcion_{n}': self.tope_9,
        }
        return ctx


@dataclass
class DatosEscrito:
    """Estructura principal con todos los campos del escrito de liquidación.

    Mapea 1:1 con el formulario HTML y con las variables del template docx.
    Diseñado para ser extensible: agregar campos futuros = agregar atributos aquí.
    """

    # --- Tipo de escrito ---
    tipo_escrito: str = ""  # 'impugnacion', 'readecuacion', 'primera_vez'

    # --- Datos del caso ---
    nombre_caratula: str = ""
    numero_expte: str = ""
    anio_expte: str = ""

    # --- Haberes ---
    haber_reclamado: str = ""
    haber_percibido: str = ""
    fecha_haber_reclamado: str = ""
    haber_de_alta: str = ""

    # --- Fechas ---
    fecha_inicial_de_pago: str = ""
    fecha_de_cierre: str = ""
    fecha_intereses: str = ""

    # --- Opciones de liquidación (1 a 4) ---
    opciones: list = field(default_factory=list)

    # --- Inconstitucionalidades ---
    inconstitucionalidad_si: bool = False
    inconstitucionalidad_27426_si: bool = False
    inconstitucionalidad_27541_si: bool = False
    inconstitucionalidad_27609_si: bool = False
    inconstitucionalidad_decreto_274_si: bool = False

    # --- Motivos de impugnación ---
    no_reajusta_pbu: bool = False
    corta_intereses_tres_meses: bool = False
    reajusta_haber: bool = False
    no_toma_sumas_rem: bool = False
    no_corrige_error_material: bool = False

    # --- Sala ---
    sala: str = ""  # '1' o '2'

    # --- Otros condicionales ---
    reparacion_historica: bool = False
    tuvo_pagos: bool = False
    
    # --- Pagos (texto descriptivo) ---
    pagos_descripcion: str = ""

    @classmethod
    def from_form(cls, form_data) -> 'DatosEscrito':
        """Construye un DatosEscrito desde un request.form de Flask.

        Parsea checkboxes como booleanos, construye la lista de opciones
        dinámicamente según cuántas existan en el formulario.
        """
        datos = cls()

        # Tipo de escrito
        datos.tipo_escrito = form_data.get('tipo_escrito', '')

        # Datos del caso
        datos.nombre_caratula = form_data.get('nombre_caratula', '')
        datos.numero_expte = form_data.get('numero_expte', '')
        datos.anio_expte = form_data.get('anio_expte', '')

        # Haberes
        datos.haber_reclamado = form_data.get('haber_reclamado', '')
        datos.haber_percibido = form_data.get('haber_percibido', '')
        datos.fecha_haber_reclamado = form_data.get('fecha_haber_reclamado', '')
        datos.haber_de_alta = form_data.get('haber_de_alta', '')

        # Fechas
        datos.fecha_inicial_de_pago = form_data.get('fecha_inicial_de_pago', '')
        datos.fecha_de_cierre = form_data.get('fecha_de_cierre', '')
        datos.fecha_intereses = form_data.get('fecha_intereses', '')

        # Opciones de liquidación (dinámicas, 1 a 4)
        datos.opciones = []
        for i in range(1, 5):
            # Solo agregar si tiene al menos movilidad o total
            movilidad = form_data.get(f'movilidad_opcion_{i}', '').strip()
            total = form_data.get(f'total_opcion_{i}', '').strip()
            if movilidad or total:
                opcion = OpcionLiquidacion(
                    numero=i,
                    movilidad=movilidad,
                    capital=form_data.get(f'capital_opcion_{i}', ''),
                    intereses=form_data.get(f'intereses_opcion_{i}', ''),
                    total=total,
                    tope_9=form_data.get(f'tope_9_opcion_{i}', '') == 'on',
                )
                datos.opciones.append(opcion)

        # Inconstitucionalidades
        datos.inconstitucionalidad_27426_si = form_data.get('inconstitucionalidad_27426_si', '') == 'on'
        datos.inconstitucionalidad_27541_si = form_data.get('inconstitucionalidad_27541_si', '') == 'on'
        datos.inconstitucionalidad_27609_si = form_data.get('inconstitucionalidad_27609_si', '') == 'on'
        datos.inconstitucionalidad_decreto_274_si = form_data.get('inconstitucionalidad_decreto_274_si', '') == 'on'
        # Si alguna inconstitucionalidad está marcada, el flag general es True
        datos.inconstitucionalidad_si = any([
            datos.inconstitucionalidad_27426_si,
            datos.inconstitucionalidad_27541_si,
            datos.inconstitucionalidad_27609_si,
            datos.inconstitucionalidad_decreto_274_si,
        ])

        # Motivos de impugnación
        datos.no_reajusta_pbu = form_data.get('no_reajusta_pbu', '') == 'on'
        datos.corta_intereses_tres_meses = form_data.get('corta_intereses_tres_meses', '') == 'on'
        datos.reajusta_haber = form_data.get('reajusta_haber', '') == 'on'
        datos.no_toma_sumas_rem = form_data.get('no_toma_sumas_rem', '') == 'on'
        datos.no_corrige_error_material = form_data.get('no_corrige_error_material', '') == 'on'

        # Sala
        datos.sala = form_data.get('sala', '')

        # Otros
        datos.reparacion_historica = form_data.get('reparacion_historica', '') == 'on'
        datos.tuvo_pagos = form_data.get('tuvo_pagos', '') == 'on'
        datos.pagos_descripcion = form_data.get('pagos_descripcion', '')

        return datos

    def to_template_context(self) -> dict:
        """Convierte a dict con los nombres EXACTOS que espera el template docx.

        Importante: el docx usa caracteres con tilde (ó, á) en algunos nombres
        de condicionales. Este método mapea los nombres internos (sin tilde)
        a los nombres del docx (con tilde).
        """
        ctx = {}

        # --- Tipo de escrito (condicionales mutuamente excluyentes) ---
        ctx['impugnación'] = self.tipo_escrito == 'impugnacion'
        ctx['readecuación'] = self.tipo_escrito == 'readecuacion'
        ctx['primera_vez'] = self.tipo_escrito == 'primera_vez'

        # --- Datos del caso ---
        ctx['nombre_caratula'] = self.nombre_caratula
        ctx['numero_expte'] = self.numero_expte
        ctx['año_expte'] = self.anio_expte

        # --- Haberes ---
        ctx['haber_reclamado'] = self.haber_reclamado
        ctx['haber_percibido'] = self.haber_percibido
        ctx['fecha_haber_reclamado'] = self.fecha_haber_reclamado
        ctx['haber_de_alta'] = self.haber_de_alta

        # --- Fechas ---
        ctx['fecha_inicial_de_pago'] = self.fecha_inicial_de_pago
        ctx['fecha_de_cierre'] = self.fecha_de_cierre
        ctx['fecha_intereses'] = self.fecha_intereses

        # --- Opciones de liquidación ---
        # El docx usa opción_1 (siempre presente), opción_3 y opción_4 como condicionales
        # opción_2 siempre se muestra (no tiene condicional en el docx)
        opciones_presentes = {op.numero for op in self.opciones}
        ctx['opción_1'] = 1 in opciones_presentes
        ctx['opción_3'] = 3 in opciones_presentes
        ctx['opción_4'] = 4 in opciones_presentes

        for opcion in self.opciones:
            ctx.update(opcion.to_template_context())

        # Rellenar opciones vacías para evitar errores en docxtpl
        for i in range(1, 5):
            if i not in opciones_presentes:
                ctx.setdefault(f'movilidad_opcion_{i}', '')
                ctx.setdefault(f'capital_opcion_{i}', '')
                ctx.setdefault(f'intereses_opcion_{i}', '')
                ctx.setdefault(f'total_opcion_{i}', '')
                ctx.setdefault(f'tope_9_opcion_{i}', False)

        # --- Inconstitucionalidades (nombres sin puntos, matching la plantilla corregida) ---
        ctx['inconstitucionalidad_si'] = self.inconstitucionalidad_si
        ctx['inconstitucionalidad_27426_si'] = self.inconstitucionalidad_27426_si
        ctx['inconstitucionalidad_27541_si'] = self.inconstitucionalidad_27541_si
        ctx['inconstitucionalidad_27609_si'] = self.inconstitucionalidad_27609_si
        ctx['inconstitucionalidad_27609'] = self.inconstitucionalidad_27609_si
        ctx['inconstitucionalidad_decreto_274_si'] = self.inconstitucionalidad_decreto_274_si

        # --- Motivos de impugnación ---
        ctx['no_reajusta_pbu'] = self.no_reajusta_pbu
        ctx['corta_intereses_tres_meses'] = self.corta_intereses_tres_meses
        ctx['reajusta_haber'] = self.reajusta_haber
        ctx['no_toma_sumas_rem'] = self.no_toma_sumas_rem
        ctx['no_corrige_error_material'] = self.no_corrige_error_material

        # --- Sala ---
        ctx['sala_1'] = self.sala == '1'
        ctx['sala_2'] = self.sala == '2'

        # --- Otros ---
        ctx['reparación_historica'] = self.reparacion_historica
        ctx['if_tuvo_pagos'] = self.tuvo_pagos

        return ctx
