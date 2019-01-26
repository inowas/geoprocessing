import os
from flask import Flask, request, redirect, url_for, render_template
import json
import uuid
from osgeo import gdal
from skimage.transform import resize

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = {'txt', 'png', 'jpg', 'jpeg', 'gif', 'tif', 'tiff', 'pdf'}

app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def valid_gdal_file(filename):
    dataset = gdal.Open(os.path.join(app.config['UPLOAD_FOLDER'], filename), gdal.GA_ReadOnly)
    if type(dataset) is not gdal.Dataset:
        return False
    return True


def file_extension(filename):
    if '.' in filename:
        return '_' + filename.rsplit('.', 1)[1]


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']

        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return 'No selected file'

        if not allowed_file(file.filename):
            return 'Extension not allowed.'

        filename = str(uuid.uuid4()) + file_extension(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if not valid_gdal_file(filename):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return 'File is not a valid GDAL-File'

        return redirect(url_for('file_metadata', filename=filename))

    return render_template('upload.html')


def get_metadata(filename):
    dataset = gdal.Open(os.path.join(app.config['UPLOAD_FOLDER'], filename), gdal.GA_ReadOnly)
    if type(dataset) is not gdal.Dataset:
        return 'Invalid GDAL-FILE'

    metadata = {
        'driver': dataset.GetDriver().ShortName,
        'rasterXSize': dataset.RasterXSize,
        'rasterYSize': dataset.RasterYSize,
        'rasterCount': dataset.RasterCount,
        'projection': dataset.GetProjection()
    }

    geotransform = dataset.GetGeoTransform()
    if geotransform:
        metadata['origin'] = [geotransform[0], geotransform[3]]
        metadata['pixelSize'] = [geotransform[1], geotransform[5]]

    return metadata


def interpolate(data2d, target_width, target_height, method):
    return resize(data2d, (int(target_height), int(target_width)), mode=method, preserve_range=True)


def get_data(filename, width=False, height=False, method='wrap'):
    dataset = gdal.Open(os.path.join(app.config['UPLOAD_FOLDER'], filename), gdal.GA_ReadOnly)
    if type(dataset) is not gdal.Dataset:
        return 'Invalid GDAL-FILE'

    data = []
    for iBand in range(1, dataset.RasterCount + 1):
        band = dataset.GetRasterBand(iBand)
        band_data = band.ReadAsArray()

        if width and height:
            band_data = interpolate(data2d=band_data, target_width=width, target_height=height, method=method)

        data.append(band_data.tolist())

    return data


@app.route('/uploads/<filename>')
def file_metadata(filename):
    return json.dumps(get_metadata(filename))


@app.route('/uploads/<filename>/data')
@app.route('/uploads/<filename>/data/<width>/<height>')
def file_data(filename, width=False, height=False):
    return json.dumps(get_data(filename, width, height))


if __name__ == '__main__':

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    app.secret_key = '2349978342978342907889709154089438989043049835890'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.debug = True

    app.run(debug=True, host='0.0.0.0')