from gevent import monkey
monkey.patch_all()

import os
import io
import shutil
import zipfile
import tempfile
from flask import Flask, request, render_template, jsonify, send_file, after_this_request, send_from_directory

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp'

# --- Create necessary folders ---
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Main Page Route ---
@app.route('/')
def home():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', files=files)

# --- Chunked Upload Route ---
@app.route('/upload-chunk', methods=['POST'])
def upload_chunk():
    upload_id = request.headers.get('X-Upload-ID')
    chunk_index = int(request.headers.get('X-Chunk-Index'))
    total_chunks = int(request.headers.get('X-Total-Chunks'))
    filename = request.headers.get('X-File-Name')

    if not all([upload_id, filename]):
        return jsonify({"error": "Missing required headers"}), 400

    temp_dir = os.path.join(TEMP_FOLDER, upload_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    chunk_path = os.path.join(temp_dir, str(chunk_index))
    with open(chunk_path, 'wb') as f:
        f.write(request.data)

    try:
        uploaded_chunks = len(os.listdir(temp_dir))
    except FileNotFoundError:
        return jsonify({"success": True, "message": "Chunk processed by another worker."})

    if uploaded_chunks == total_chunks:
        final_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(final_path, 'wb') as f_out:
            for i in range(total_chunks):
                part_path = os.path.join(temp_dir, str(i))
                with open(part_path, 'rb') as f_in:
                    f_out.write(f_in.read())
        
        try:
            shutil.rmtree(temp_dir)
        except FileNotFoundError:
            pass
            
        return jsonify({"success": True, "message": "File reassembled successfully"})

    return jsonify({"success": True, "message": "Chunk received"})

# --- Multi-File Zip Download Route ---
@app.route('/download-zip', methods=['POST'])
def download_zip():
    data = request.get_json()
    filenames = data.get('filenames', [])

    if not filenames:
        return jsonify({"error": "No files selected"}), 400

    total_size_bytes = 0
    for filename in filenames:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            total_size_bytes += os.path.getsize(file_path)

    THRESHOLD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
    use_disk_strategy = total_size_bytes > THRESHOLD_BYTES

    if use_disk_strategy:
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in filenames:
                if '..' in filename or filename.startswith('/'): continue
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=filename)
        temp_zip.close()

        @after_this_request
        def remove_file(response):
            try:
                os.remove(temp_zip.name)
            except Exception as error:
                app.logger.error("Error removing temporary zip file", error)
            return response

        return send_file(
            temp_zip.name, mimetype='application/zip',
            as_attachment=True, download_name='download_large.zip'
        )
    else:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in filenames:
                if '..' in filename or filename.startswith('/'): continue
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=filename)
        
        memory_file.seek(0)
        
        return send_file(
            memory_file, mimetype='application/zip',
            as_attachment=True, download_name='download.zip'
        )

# --- Single File Download Route ---
@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)