from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template('menu.html')

@app.route('/calculadora_percibido')
def Calculadora_Percibido():
    return render_template('prueba.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)