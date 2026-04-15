
from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('indexMQTT.html')

if __name__ == '__main__':
    # # HTTPS obligatorio para que el navegador permita acceso al micrófono (control por voz)
    # # 'adhoc' genera el certificado automáticamente (requiere pyopenssl)
    # app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False,
    #         ssl_context='adhoc')
    app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)