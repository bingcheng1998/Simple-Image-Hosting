import os
import base64
from datetime import datetime
from flask import Flask, request, send_from_directory, abort, render_template, Response, stream_with_context
from flask_httpauth import HTTPBasicAuth
import yaml
import requests
import shortuuid

app = Flask(__name__)
auth = HTTPBasicAuth()

YAML_FILE_PATH = "config.yaml"
USER_CONFIG_FILE_PATH = "config.user.yaml"

if os.path.exists(USER_CONFIG_FILE_PATH):
    file_path = USER_CONFIG_FILE_PATH
else:
    file_path = YAML_FILE_PATH

with open(file_path, 'r') as f:
    config = yaml.safe_load(f)

STORAGE_ROOT = config['storage']['root_directory']
USERNAME = config['auth']['username']
PASSWORD = config['auth']['password']

os.makedirs(STORAGE_ROOT, exist_ok=True)

@auth.verify_password
def verify_password(username, password):
    return PASSWORD == password and username == USERNAME

def encode_filename(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    timestamp = datetime.now().timestamp()
    print('timestamp', timestamp)
    encoded_info = base64.urlsafe_b64encode(f"{timestamp}%{ext}".encode()).decode().rstrip('=')
    short_uuid = shortuuid.uuid() 
    return f"{short_uuid}.{encoded_info}"

def decode_filename(encoded_filename):
    parts = encoded_filename.split('.')
    encoded_info = parts[-1]
    decoded_info = base64.urlsafe_b64decode(encoded_info + '==').decode()
    print('decoded_info', decoded_info)
    timestamp, ext = decoded_info.split('%')
    date_str = datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d")
    return date_str, ext

def get_storage_path(filename):
    date_str, ext = decode_filename(filename)
    return os.path.join(STORAGE_ROOT, ext, date_str, filename), ext

@app.route('/upload', methods=['POST'])
@auth.login_required
def upload_file():
    if 'file' not in request.files:
        abort(400, 'No file part')

    file = request.files['file']
    if file.filename == '':
        abort(400, 'No selected file')

    ext = file.filename.rsplit('.', 1)[-1].lower()
    supported_types = (
        # 视频
        'mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm', 'mpeg', 'mpg', 'm4v', '3gp',
        # 音频
        'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma',
        # 图片
        'png', 'jpeg', 'jpg', 'gif', 'webp', 'bmp', 'tiff', 'svg',
    )
    if ext.lower() not in supported_types:
        abort(400, 'Unsupported file type')

    filename = encode_filename(file.filename)
    filepath, _ = get_storage_path(filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)

    return {'id': filename}, 201

@app.route('/files/<filename>')
def get_file(filename):
    filepath, ext = get_storage_path(filename)
    return send_from_directory(os.path.dirname(filepath), os.path.basename(filepath), 
            download_name=f'{datetime.now().strftime("%Y-%m-%d-%H_%M_%S")}.{ext}')

@app.route('/local_proxy/<path:url>')
@auth.login_required
def local_proxy(url):
    try:
        response = requests.get(url, stream=True)
        return Response(stream_with_context(response.iter_content(chunk_size=1024)),
                        content_type=response.headers['content-type'])
    except requests.exceptions.RequestException as e:
        abort(500, f"Error fetching local resource: {e}")

@app.route('/')
@auth.login_required
def index():
    return render_template('upload.html', username=USERNAME, password=PASSWORD)

if __name__ == '__main__':
    app.run(debug=True, port=8094, host="0.0.0.0")
