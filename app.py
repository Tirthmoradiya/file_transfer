import sys
import os
import io
import shutil
import zipfile
import tempfile
import time
import json
from datetime import datetime
from flask import Flask, request, render_template, jsonify, send_file, after_this_request, send_from_directory, abort
from werkzeug.utils import secure_filename

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- App Settings (Initial placeholders, to be set by GUI) ---
UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp'
AUTH_TOKEN = None
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar', '7z', 'csv', 'mp4', 'mp3', 'mkv'
}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

app = Flask(__name__, 
            template_folder=get_resource_path('templates'),
            static_folder=get_resource_path('static'))

def update_app_config(upload_dir, temp_dir, auth_token=None, allowed_extensions=None, max_content_length=None):
    global UPLOAD_FOLDER, TEMP_FOLDER, AUTH_TOKEN, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
    UPLOAD_FOLDER = upload_dir
    TEMP_FOLDER = temp_dir
    AUTH_TOKEN = auth_token
    
    if allowed_extensions is not None:
        if isinstance(allowed_extensions, str):
            ALLOWED_EXTENSIONS = {ext.strip().lower().lstrip('.') for ext in allowed_extensions.split(',') if ext.strip()}
        else:
            ALLOWED_EXTENSIONS = set(allowed_extensions)
            
    if max_content_length is not None:
        MAX_CONTENT_LENGTH = max_content_length

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
        
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


def _is_allowed_filename(name: str) -> bool:
    if not ALLOWED_EXTENSIONS:  # if empty, allow all
        return True
    _, dot, ext = name.rpartition('.')
    return bool(dot) and ext.lower() in ALLOWED_EXTENSIONS


def _authorized() -> bool:
    if not AUTH_TOKEN:
        return True
    header_token = request.headers.get('X-Auth-Token')
    query_token = request.args.get('token')
    return header_token == AUTH_TOKEN or query_token == AUTH_TOKEN


def _require_auth():
    if not _authorized():
        abort(401)


def _cleanup_orphan_temp_dirs():
    now = time.time()
    try:
        if not os.path.exists(TEMP_FOLDER):
            return
        for name in os.listdir(TEMP_FOLDER):
            path = os.path.join(TEMP_FOLDER, name)
            if os.path.isdir(path):
                try:
                    age = now - os.path.getmtime(path)
                    if age > TEMP_CLEANUP_MAX_AGE_SECS:
                        shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    app.logger.exception("Error during temp cleanup for %s", path)
    except Exception:
        app.logger.exception("Error scanning temp folder for cleanup")

# --- Main Page Route ---
@app.route('/')
def home():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', files=files)

# --- Chunked Upload Route ---
@app.route('/upload-chunk', methods=['POST'])
def upload_chunk():
    _require_auth()
    upload_id = request.headers.get('X-Upload-ID')
    chunk_index = int(request.headers.get('X-Chunk-Index'))
    total_chunks = int(request.headers.get('X-Total-Chunks'))
    filename = request.headers.get('X-File-Name')

    if not all([upload_id, filename]):
        return jsonify({"error": "Missing required headers"}), 400

    # Sanitize and validate filename
    safe_filename = secure_filename(filename)
    if not safe_filename:
        return jsonify({"error": "Invalid filename"}), 400
    if not _is_allowed_filename(safe_filename):
        return jsonify({"error": "File type not allowed"}), 400

    temp_dir = os.path.join(TEMP_FOLDER, upload_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    chunk_path = os.path.join(temp_dir, str(chunk_index))
    with open(chunk_path, 'wb') as f:
        f.write(request.data)

    try:
        # Robust completeness check: ensure all indexed chunk files exist
        present = {int(n) for n in os.listdir(temp_dir) if n.isdigit()}
    except FileNotFoundError:
        return jsonify({"success": True, "message": "Chunk processed by another worker."})

    if all(i in present for i in range(total_chunks)):
        # Attempt to "lock" the reassembly by renaming the temp directory
        processing_dir = os.path.join(TEMP_FOLDER, f"processing_{upload_id}")
        try:
            os.rename(temp_dir, processing_dir)
        except OSError:
            # Another worker already renamed it or it's gone
            return jsonify({"success": True, "message": "File is being processed or already reassembled"})

        final_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        try:
            with open(final_path, 'wb') as f_out:
                for i in range(total_chunks):
                    part_path = os.path.join(processing_dir, str(i))
                    with open(part_path, 'rb') as f_in:
                        f_out.write(f_in.read())
            
            shutil.rmtree(processing_dir, ignore_errors=True)
            return jsonify({"success": True, "message": "File reassembled successfully"})
        except Exception as e:
            # If reassembly fails, try to move it back so it can be retried? 
            # Or just cleanup. For simplicity, we'll log and cleanup.
            app.logger.exception("Error reassembling file %s", safe_filename)
            shutil.rmtree(processing_dir, ignore_errors=True)
            return jsonify({"error": "Failed to reassemble file"}), 500

    return jsonify({"success": True, "message": "Chunk received"})

# --- Multi-File Zip Download Route ---
@app.route('/download-zip', methods=['POST'])
def download_zip():
    _require_auth()
    data = request.get_json(silent=True)
    filenames = []
    if data and isinstance(data, dict):
        filenames = data.get('filenames', [])
    else:
        # Fallback to form submission (e.g., from an HTML form)
        if 'filenames' in request.form:
            try:
                filenames = json.loads(request.form['filenames'])
            except Exception:
                filenames = []

    if not filenames:
        return jsonify({"error": "No files selected"}), 400

    total_size_bytes = 0
    safe_names = []
    for filename in filenames:
        safe_name = secure_filename(filename)
        if not safe_name:
            continue
        file_path = os.path.join(UPLOAD_FOLDER, safe_name)
        if os.path.exists(file_path):
            total_size_bytes += os.path.getsize(file_path)
            safe_names.append(safe_name)

    THRESHOLD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
    use_disk_strategy = total_size_bytes > THRESHOLD_BYTES

    if use_disk_strategy:
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name in safe_names:
                file_path = os.path.join(UPLOAD_FOLDER, name)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=name)
        temp_zip.close()

        @after_this_request
        def remove_file(response):
            try:
                os.remove(temp_zip.name)
            except Exception:
                app.logger.exception("Error removing temporary zip file")
            return response

        response = send_file(
            temp_zip.name, mimetype='application/zip',
            as_attachment=True, download_name='download_large.zip',
            conditional=True
        )
        # Hint that we support range requests
        response.headers['Accept-Ranges'] = 'bytes'
        return response
    else:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name in safe_names:
                file_path = os.path.join(UPLOAD_FOLDER, name)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=name)
        
        memory_file.seek(0)
        
        response = send_file(
            memory_file, mimetype='application/zip',
            as_attachment=True, download_name='download.zip'
        )
        response.headers['Accept-Ranges'] = 'bytes'
        return response

# --- Single File Download Route ---
@app.route('/uploads/<filename>')
def download_file(filename):
    _require_auth()
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(404)
    response = send_from_directory(
        app.config['UPLOAD_FOLDER'], safe_name,
        as_attachment=True, conditional=True
    )
    response.headers['Accept-Ranges'] = 'bytes'
    return response


# --- Utility Endpoints ---
@app.route('/files')
def list_files():
    _require_auth()
    try:
        files = []
        for filename in sorted(os.listdir(app.config['UPLOAD_FOLDER'])):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                stats = os.stat(file_path)
                files.append({
                    "name": filename,
                    "size": stats.st_size,
                    "mtime": stats.st_mtime
                })
        return jsonify({"files": files})
    except Exception:
        app.logger.exception("Error listing files")
        return jsonify({"files": []}), 500


@app.route('/delete', methods=['POST'])
def delete_file():
    _require_auth()
    data = request.get_json(silent=True)
    if not data or 'filename' not in data:
        return jsonify({"error": "Filename required"}), 400
    
    filename = secure_filename(data['filename'])
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return jsonify({"success": True, "message": f"Deleted {filename}"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "File not found"}), 404


@app.route('/rename', methods=['POST'])
def rename_file():
    _require_auth()
    data = request.get_json(silent=True)
    if not data or 'old_name' not in data or 'new_name' not in data:
        return jsonify({"error": "Old and new names required"}), 400
    
    old_name = secure_filename(data['old_name'])
    new_name = secure_filename(data['new_name'])
    
    old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_name)
    new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_name)
    
    if not os.path.exists(old_path):
        return jsonify({"error": "Source file not found"}), 404
    if os.path.exists(new_path):
        return jsonify({"error": "Destination already exists"}), 400
    
    try:
        os.rename(old_path, new_path)
        return jsonify({"success": True, "message": f"Renamed to {new_name}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/upload-status', methods=['GET'])
def upload_status():
    """Return existing chunk indices for a given upload_id."""
    _require_auth()
    upload_id = request.args.get('upload_id')
    if not upload_id:
        return jsonify({"error": "upload_id required"}), 400
    temp_dir = os.path.join(TEMP_FOLDER, upload_id)
    if not os.path.exists(temp_dir):
        return jsonify({"present": []})
    present = [int(n) for n in os.listdir(temp_dir) if n.isdigit()]
    present.sort()
    return jsonify({"present": present})


# Perform initial temp cleanup at startup
_cleanup_orphan_temp_dirs()