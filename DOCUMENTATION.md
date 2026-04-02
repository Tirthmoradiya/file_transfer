# Technical Documentation - Transfer

This document provides more in-depth technical details about the architecture, implementation, and advanced configuration of the **Transfer** utility.

## 🏗️ Architecture Design

The application follows a **Hybrid Threading Model** that integrates a Flask web server, gevent's high-concurrency event-loop, and a PyQt6 desktop GUI.

### 1. Main Thread (PyQt6)
- Manages the entire user interface and user interactions.
- Responsible for responding to window resizing and layout toggling.
- Monitors the `refresh_timer` to sync the file list display.

### 2. Server Thread (gevent + Flask)
- Spawns a dedicated background thread for the WSGI server.
- Uses `gevent.pywsgi.WSGIServer` to handle incoming HTTP requests.
- **Connection Pooling**: The `spawn` parameter (configured via "Max Workers" in the GUI) limits the number of concurrent greenlets, ensuring the server remains stable under heavy load.

## ⚙️ Advanced Settings Explained

### **Max Workers**
The number of concurrent connections allowed by the server. 
- **Low (1-4)**: Best for single-user transfers and low-memory devices.
- **High (10-50)**: Recommended when multiple devices are uploading/downloading simultaneously.

### **Request Timeout**
The maximum time (in seconds) the server will wait for a request to complete. This is crucial for long-running uploads over slow or unstable Wi-Fi.

### **Allowed Extensions**
A security layer that restricts files by their suffix. 
- Input: `txt, pdf, png`
- Implementation: The backend sanitizes filenames and checks the extension against this case-insensitive set before saving any data.

### **Max Upload Size**
A hard cap on the size of an individual file. This setting updates Flask's `MAX_CONTENT_LENGTH` configuration in real-time.

## 🛠️ Performance Tuning

### **Chunked Transfers**
The web client splits files into 5MB chunks (default). This allows:
1. **Resumable Uploads**: If a connection drops, only the current chunk needs re-uploading.
2. **Parallelism**: Multiple chunks can be sent to the server's worker pool at once.

### **Gevent Monkey Patching**
In `main_gui.py` and `run.py`, we use `gevent.monkey.patch_all()`. This transforms standard Python blocking calls (like networking) into non-blocking greenlets, allowing the server to handle hundreds of concurrent operations efficiently.

## ⚠️ Troubleshooting

- **Server Won't Start**: Check if the selected port is already in use by another application.
- **Access Denied**: Ensure the "Uploads Directory" has read/write permissions for the current user.
- **Mobile Connection Fails**: Ensure your phone and PC are on the same Wi-Fi network and that your firewall allows traffic on the selected port.
