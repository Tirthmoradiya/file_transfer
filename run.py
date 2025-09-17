from gevent import monkey
monkey.patch_all()

import os
import socket
import qrcode
import multiprocessing
from gunicorn.app.base import BaseApplication

# --- Import your Flask app instance ---
from app import app

# --- Custom Gunicorn Application Class ---
class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    # 1. Get host IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host_ip = s.getsockname()[0]
        s.close()
    except OSError:
        host_ip = '127.0.0.1'

    # 2. Set server port
    SERVER_PORT = 5000
    
    # 3. Print QR code and info
    url = f"http://{host_ip}:{SERVER_PORT}"
    print("="*40)
    print(f"🚀 Starting server...")
    print(f"   Access the server at this IP Address:")
    print(f"   {url}")
    print("="*40)
    print("Scan this QR code with your phone:")
    qr = qrcode.QRCode()
    qr.add_data(url)
    qr.print_ascii(invert=True)
    print("\n")
    
    # 4. Configure and run Gunicorn
    options = {
        'bind': f'0.0.0.0:{SERVER_PORT}',
        'workers': 1,
        'worker_class': 'gevent',
        'timeout': 300,
    }

    print("Gunicorn is now running. Press CTRL+C to quit.")
    StandaloneApplication(app, options).run()