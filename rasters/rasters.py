import json
import os
import time
import uuid

from flask import Blueprint, request, redirect, render_template
from flask_cors import cross_origin

from osgeo import gdal
from skimage.transform import resize

from dotenv import load_dotenv

load_dotenv()

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER") if not None else './uploads'
ALLOWED_EXTENSIONS = {'txt', 'png', 'jpg', 'jpeg', 'gif', 'tif', 'tiff', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

rasters = Blueprint(
    'rasters',
    __name__,
    url_prefix='/rasters',
    template_folder='templates',
    static_folder='../static'
)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def valid_gdal_file(filename):
    dataset = gdal.Open(os.path.join(UPLOAD_FOLDER, filename), gdal.GA_ReadOnly)
    if type(dataset) is not gdal.Dataset:
        return False
    return True


def file_extension(filename):
    if '.' in filename:
        return '_' + filename.rsplit('.', 1)[1]


@rasters.route('/', methods=['GET', 'POST'])
@cross_origin()
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
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        if not valid_gdal_file(filename):
            os.remove(os.path.join(UPLOAD_FOLDER, filename))
            return 'File is not a valid GDAL-File'

        return json.dumps({
            'status': 200,
            'hash': filename,
            'get_metadata': '/' + filename,
            'get_data': '/' + filename + '/data',
            'get_scaled_data': '/' + filename + '/data/<width>/<height>'
        })

    return render_template('upload.html')


def get_metadata(filename):
    dataset = gdal.Open(os.path.join(UPLOAD_FOLDER, filename), gdal.GA_ReadOnly)
    print(dataset)
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
    return resize(data2d, (int(target_height), int(target_width)), order=method, mode='wrap', preserve_range=True)


# delete files older then 1 hour
def cleanup():
    now = time.time()
    for f in os.listdir(UPLOAD_FOLDER):
        if os.stat(os.path.join(UPLOAD_FOLDER, f)).st_mtime < now - 3600:
            os.remove(os.path.join(UPLOAD_FOLDER, f))


def get_data(filename, width=False, height=False, method=1):
    dataset = gdal.Open(os.path.join(UPLOAD_FOLDER, filename), gdal.GA_ReadOnly)
    if type(dataset) is not gdal.Dataset:
        os.remove(os.path.join(UPLOAD_FOLDER, filename))
        return 'Invalid GDAL-FILE'

    data = []
    for iBand in range(1, dataset.RasterCount + 1):
        band = dataset.GetRasterBand(iBand)
        band_data = band.ReadAsArray()

        if width and height:
            band_data = interpolate(data2d=band_data, target_width=width, target_height=height, method=method)

        data.append(band_data.tolist())

    return data


@rasters.route('/<filename>')
@cross_origin()
def file_metadata(filename):
    cleanup()
    return json.dumps(get_metadata(filename))


@rasters.route('/<filename>/data')
@rasters.route('/<filename>/data/<width>/<height>')
@rasters.route('/<filename>/data/<width>/<height>/<method>')
@cross_origin()
def file_data(filename, width=False, height=False, method=1):
    return json.dumps(get_data(filename, width, height, int(method)))
