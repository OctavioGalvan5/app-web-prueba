import plotly.graph_objects as go
import io
import base64
from services.calculos import formatear_dinero

def crear_grafico(datos, nombre_grafico):
    etiquetas = ['IPC', 'RIPTE', 'UMA', 'Movilidad de Sentencia', 'Ley 27426']
    valores = datos
    resultados = list(map(formatear_dinero, valores))
    # Crear el gráfico
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
        marker_color=['blue', 'orange', 'green', 'red', 'purple'],
        text=resultados, textposition='auto'
    ))

    # Actualizar el diseño del gráfico
    fig.update_layout(
        title=nombre_grafico, 
        xaxis_title='Movilidades', 
        yaxis_title='Pesos',
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