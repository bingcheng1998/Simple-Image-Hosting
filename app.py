import os
import uuid
from flask import Flask, request, send_from_directory, abort
from werkzeug.security import check_password_hash
from flask_httpauth import HTTPBasicAuth
import yaml

app = Flask(__name__)
auth = HTTPBasicAuth()

YAML_FILE_PATH = "config.yaml"
USER_CONFIG_FILE_PATH = "config.user.yaml"

if os.path.exists(USER_CONFIG_FILE_PATH):
    file_path = USER_CONFIG_FILE_PATH
else:
    file_path = YAML_FILE_PATH
        
# 读取 YAML 配置
with open(file_path, 'r') as f:
    config = yaml.safe_load(f)

STORAGE_ROOT = config['storage']['root_directory']
USERNAME = config['auth']['username']
PASSWORD = config['auth']['password']

# 创建图片存储目录（如果不存在）
os.makedirs(STORAGE_ROOT, exist_ok=True)

# HTTP 基本认证验证
@auth.verify_password
def verify_password(username, password):
    return check_password_hash(PASSWORD, password) and username == USERNAME

# 上传图片
@app.route('/upload', methods=['POST'])
@auth.login_required  # 需要身份验证
def upload_image():
    if 'file' not in request.files:
        abort(400, 'No file part')

    file = request.files['file']
    if file.filename == '':
        abort(400, 'No selected file')

    # 生成唯一文件名
    ext = file.filename.rsplit('.', 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"

    # 保存图片
    filepath = os.path.join(STORAGE_ROOT, filename)
    file.save(filepath)

    return {'id': filename}, 201

# 获取图片
@app.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    return send_from_directory(STORAGE_ROOT, filename)

if __name__ == '__main__':
    app.run(debug=True)  # 生产环境禁用 debug 模式
