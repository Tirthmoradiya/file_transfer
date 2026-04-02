import sys
import os
import socket
import threading
import qrcode
import shutil
import webbrowser
from io import BytesIO
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QFileDialog, QFrame, 
                             QStackedWidget, QProgressBar, QScrollArea, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage, QColor, QPalette

# Import the Flask setup
from app import app, update_app_config

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

class ServerThread(threading.Thread):
    def __init__(self, host, port, spawn=None):
        super().__init__()
        self.host = host
        self.port = port
        self.spawn = spawn
        self.daemon = True

    def run(self):
        from gevent.pywsgi import WSGIServer
        self.server = WSGIServer((self.host, self.port), app, spawn=self.spawn)
        self.server.serve_forever()

class AppStyles:
    MAIN_STYLE = """
        QMainWindow {
            background-color: #0f172a;
        }
        QWidget#central-widget {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1e1b4b);
        }
        QLabel {
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
        }
        QLineEdit {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 10px;
            color: #f8fafc;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #6366f1;
        }
        QPushButton {
            background-color: #6366f1;
            color: white;
            border-radius: 8px;
            padding: 12px 20px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #4f46e5;
        }
        QPushButton#secondary-btn {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        QPushButton#secondary-btn:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        QPushButton#action-btn {
            background-color: #10b981;
        }
        QPushButton#action-btn:hover {
            background-color: #059669;
        }
        QFrame#card {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
        }
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QListWidget {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: #f8fafc;
            outline: none;
            padding: 5px;
        }
        QListWidget::item {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        QListWidget::item:selected {
            background-color: rgba(99, 102, 241, 0.2);
            color: white;
            border-radius: 8px;
        }
    """

class TransferApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transfer Desktop")
        self.setMinimumSize(450, 600)
        
        # Main Scroll Area for responsiveness
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("main-scroll")
        self.setCentralWidget(self.scroll_area)
        
        self.central_widget = QWidget()
        self.central_widget.setObjectName("central-widget")
        self.scroll_area.setWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(30, 40, 30, 40)
        self.layout.setSpacing(20)
        
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
        
        # Refresh timer for file list
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_file_list)
        
        self.init_setup_ui()
        self.init_dashboard_ui()
        
        self.setStyleSheet(AppStyles.MAIN_STYLE)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Check if dashboard needs orientation toggle
        if hasattr(self, 'dashboard_content'):
            width = self.width()
            if width > 750:
                self.dashboard_content.set_horizontal(True)
            else:
                self.dashboard_content.set_horizontal(False)
        
    def init_setup_ui(self):
        self.setup_page = QWidget()
        layout = QVBoxLayout(self.setup_page)
        layout.setSpacing(15)
        
        # Header
        title = QLabel("Server Setup")
        title.setStyleSheet("font-size: 32px; font-weight: 800;")
        layout.addWidget(title)
        
        subtitle = QLabel("Configure your local file transfer server")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 15px; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Folder Selection
        folder_card = QFrame()
        folder_card.setObjectName("card")
        f_layout = QVBoxLayout(folder_card)
        f_layout.addWidget(QLabel("Uploads Directory"))
        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit(os.path.abspath("uploads"))
        self.folder_input.setReadOnly(True)
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("secondary-btn")
        browse_btn.clicked.connect(self.browse_folder)
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(browse_btn)
        f_layout.addLayout(folder_row)
        layout.addWidget(folder_card)
        
        # Settings Grid
        settings_card = QFrame()
        settings_card.setObjectName("card")
        s_layout = QVBoxLayout(settings_card)
        
        row1 = QHBoxLayout()
        # Port
        v_p = QVBoxLayout()
        v_p.addWidget(QLabel("Port"))
        self.port_input = QLineEdit("8000")
        v_p.addWidget(self.port_input)
        row1.addLayout(v_p)
        
        # Auth Token
        v_t = QVBoxLayout()
        v_t.addWidget(QLabel("Auth Token (Optional)"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("No password")
        v_t.addWidget(self.token_input)
        row1.addLayout(v_t)
        s_layout.addLayout(row1)
        
        layout.addWidget(settings_card)
        
        # Advanced Group
        advanced_card = QFrame()
        advanced_card.setObjectName("card")
        advanced_card.setStyleSheet("background-color: rgba(255,255,255,0.02);")
        adv_layout = QVBoxLayout(advanced_card)
        
        adv_header = QLabel("Performance & Security")
        adv_header.setStyleSheet("font-weight: 700; color: #818cf8; margin-bottom: 5px;")
        adv_layout.addWidget(adv_header)
        
        adv_grid = QHBoxLayout()
        # Workers
        v_w = QVBoxLayout()
        v_w.addWidget(QLabel("Max Workers"))
        self.workers_input = QLineEdit("10")
        v_w.addWidget(self.workers_input)
        adv_grid.addLayout(v_w)
        
        # Max Size
        v_s = QVBoxLayout()
        v_s.addWidget(QLabel("Max Size (MB)"))
        self.max_size_input = QLineEdit("100")
        v_s.addWidget(self.max_size_input)
        adv_grid.addLayout(v_s)
        
        # Chunk Size
        v_c = QVBoxLayout()
        v_c.addWidget(QLabel("Chunk size"))
        self.chunk_input = QLineEdit("5")
        v_c.addWidget(self.chunk_input)
        adv_grid.addLayout(v_c)
        
        adv_layout.addLayout(adv_grid)
        
        adv_layout.addWidget(QLabel("Allowed Extensions (comma separated)"))
        self.extensions_input = QLineEdit("txt,pdf,png,jpg,jpeg,zip,mp4,mp3,mkv")
        adv_layout.addWidget(self.extensions_input)
        
        layout.addWidget(advanced_card)
        
        layout.addStretch()
        
        # Start Button
        start_btn = QPushButton("Start Server")
        start_btn.setFixedHeight(50)
        start_btn.clicked.connect(self.start_server)
        layout.addWidget(start_btn)
        
        self.stacked_widget.addWidget(self.setup_page)

    def init_dashboard_ui(self):
        self.dashboard_page = QWidget()
        layout = QVBoxLayout(self.dashboard_page)
        
        # Quick Status Bar
        header_layout = QHBoxLayout()
        status_dot = QLabel("● Live")
        status_dot.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(status_dot)
        header_layout.addStretch()
        self.url_label = QLabel("http://0.0.0.0:8000")
        self.url_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #818cf8;")
        header_layout.addWidget(self.url_label)
        
        open_web_btn = QPushButton("Open in Browser")
        open_web_btn.setFixedHeight(30)
        open_web_btn.setObjectName("secondary-btn")
        open_web_btn.setStyleSheet("font-size: 12px; padding: 0 10px;")
        open_web_btn.clicked.connect(self.open_in_browser)
        header_layout.addWidget(open_web_btn)
        layout.addLayout(header_layout)

        # Responsive Container
        self.dashboard_content = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_content)
        self.dashboard_layout.setContentsMargins(0, 0, 0, 0)
        self.dashboard_layout.setSpacing(20)
        
        # QR Code Card
        qr_card = QFrame()
        qr_card.setObjectName("card")
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setStyleSheet("background-color: white; border-radius: 12px; padding: 10px;")
        qr_layout.addWidget(self.qr_label)
        
        hint = QLabel("Scan to connect mobile")
        hint.setStyleSheet("color: #94a3b8; font-size: 12px; margin-top: 10px;")
        qr_layout.addWidget(hint, alignment=Qt.AlignmentFlag.AlignCenter)
        self.dashboard_layout.addWidget(qr_card)

        # File List Card
        file_card = QFrame()
        file_card.setObjectName("card")
        file_layout = QVBoxLayout(file_card)
        
        file_header = QHBoxLayout()
        file_title = QLabel("Shared Files")
        file_title.setStyleSheet("font-weight: 700; font-size: 16px;")
        file_header.addWidget(file_title)
        
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setObjectName("secondary-btn")
        refresh_btn.clicked.connect(self.refresh_file_list)
        file_header.addWidget(refresh_btn)
        file_layout.addLayout(file_header)
        
        self.file_list_widget = QListWidget()
        self.file_list_widget.setMinimumHeight(200)
        file_layout.addWidget(self.file_list_widget)
        
        # Dashboard indicator for debug
        print("Dashboard initialized - v2 with browser support")
        
        # Actions
        actions_layout = QHBoxLayout()
        send_btn = QPushButton("Send File to Mobile")
        send_btn.setObjectName("action-btn")
        send_btn.setFixedHeight(40)
        send_btn.clicked.connect(self.share_file)
        actions_layout.addWidget(send_btn)
        file_layout.addLayout(actions_layout)
        
        self.dashboard_layout.addWidget(file_card)
        layout.addWidget(self.dashboard_content)
        
        # Stop Button at bottom
        stop_btn = QPushButton("Stop Server")
        stop_btn.setFixedHeight(40)
        stop_btn.setStyleSheet("background-color: #ef4444; margin-top: 10px;")
        stop_btn.clicked.connect(self.stop_server)
        layout.addWidget(stop_btn)
        
        # Helper to toggle layout
        def set_horizontal(horizontal):
            if horizontal and isinstance(self.dashboard_layout, QVBoxLayout):
                new_layout = QHBoxLayout()
                new_layout.setSpacing(20)
                # Move widgets
                new_layout.addWidget(qr_card, 1)
                new_layout.addWidget(file_card, 2)
                # Swap layout
                QWidget().setLayout(self.dashboard_layout) # Clear old layout
                self.dashboard_layout = new_layout
                self.dashboard_content.setLayout(new_layout)
            elif not horizontal and isinstance(self.dashboard_layout, QHBoxLayout):
                new_layout = QVBoxLayout()
                new_layout.setSpacing(20)
                new_layout.addWidget(qr_card)
                new_layout.addWidget(file_card)
                QWidget().setLayout(self.dashboard_layout)
                self.dashboard_layout = new_layout
                self.dashboard_content.setLayout(new_layout)
        
        self.dashboard_content.set_horizontal = set_horizontal
        self.stacked_widget.addWidget(self.dashboard_page)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Uploads Directory")
        if folder:
            self.folder_input.setText(folder)

    def open_in_browser(self):
        if hasattr(self, 'current_url'):
            webbrowser.open(self.current_url)

    def refresh_file_list(self):
        if not hasattr(self, 'upload_dir'):
            return
            
        try:
            files = sorted(os.listdir(self.upload_dir))
            # Filter only files
            files = [f for f in files if os.path.isfile(os.path.join(self.upload_dir, f)) and not f.startswith('.')]
            
            # Simple sync check
            current_items = [self.file_list_widget.item(i).text().split(' (')[0] for i in range(self.file_list_widget.count())]
            if files == current_items:
                return
                
            self.file_list_widget.clear()
            for filename in files:
                file_path = os.path.join(self.upload_dir, filename)
                size = os.path.getsize(file_path)
                size_str = self.format_size(size)
                item = QListWidgetItem(f"{filename} ({size_str})")
                self.file_list_widget.addItem(item)
        except Exception as e:
            print(f"Error refreshing files: {e}")

    def share_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Share")
        if file_path:
            try:
                dest = os.path.join(self.upload_dir, os.path.basename(file_path))
                if os.path.exists(dest):
                    # Maybe handle duplicates, but for now just overwrite
                    pass
                shutil.copy2(file_path, dest)
                self.refresh_file_list()
            except Exception as e:
                print(f"Error sharing file: {e}")

    def format_size(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"

    def start_server(self):
        self.upload_dir = self.folder_input.text()
        auth_token = self.token_input.text() or None
        port = int(self.port_input.text())
        
        # Advanced settings
        try:
            max_workers = int(self.workers_input.text())
            max_size_mb = int(self.max_size_input.text())
            allowed_exts = self.extensions_input.text()
        except ValueError:
            max_workers = 10
            max_size_mb = 100
            allowed_exts = "txt,pdf,png,jpg,jpeg,zip,mp4,mp3,mkv"
            
        # Update Flask config
        update_app_config(
            self.upload_dir, 
            os.path.join(self.upload_dir, ".temp"), 
            auth_token,
            allowed_extensions=allowed_exts,
            max_content_length=max_size_mb * 1024 * 1024
        )
        
        # Get IP
        ip = get_local_ip()
        url = f"http://{ip}:{port}"
        self.url_label.setText(url)
        
        # Generate QR
        qr_pixmap = self.generate_qr(url)
        self.qr_label.setPixmap(qr_pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        # Start Thread with spawn pool size
        self.server_thread = ServerThread('0.0.0.0', port, spawn=max_workers)
        self.server_thread.start()
        
        # Start refresh timer (every 3 seconds)
        self.refresh_timer.start(3000)
        self.refresh_file_list()
        
        self.current_url = url
        self.stacked_widget.setCurrentIndex(1)
        print(f"Server started at {url}. Switched to Dashboard.")

    def stop_server(self):
        # In a real app, you'd want a more graceful shutdown
        # But for this utility, we'll likely just exit the app or restart
        sys.exit(0)

    def generate_qr(self, data):
        qr = qrcode.QRCode(version=1, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert PIL image to QPixmap
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qimage = QImage.fromData(buffer.getvalue())
        return QPixmap.fromImage(qimage)

if __name__ == "__main__":
    app_qt = QApplication(sys.argv)
    window = TransferApp()
    window.show()
    sys.exit(app_qt.exec())
