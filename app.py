from flask import Flask
from flask_cors import CORS

# Blueprints
from rasters.rasters import rasters
from timeseries.timeseries import timeseries

app = Flask(__name__)
CORS(app)

if __name__ == '__main__':
    app.register_blueprint(rasters)
    app.register_blueprint(timeseries)
    app.secret_key = '2349978342978342907889709154089438989043049835890'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.debug = True

    app.run(debug=True, host='0.0.0.0')
