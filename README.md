# Transfer | Secure LAN File sharing

**Transfer** is a high-performance, personal file sharing tool designed for local networks. It combines a robust Flask backend with a beautiful, responsive PyQt6 desktop interface, making it effortless to move files between your computer and mobile devices.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-mac%20%7C%20windows%20%7C%20linux-lightgrey.svg)

## 🚀 Key Features

- **Responsive Desktop GUI**: A modern PyQt6 interface that automatically switches between Vertical (Mobile-style) and Horizontal (Desktop-wide) layouts.
- **Real-time Dashboard**: Live view of shared files with automatic synchronization across all connected devices.
- **Advanced Configuration**: Granular control over connection workers, request timeouts, and allowed file extensions.
- **Chunked & Parallel Uploads**: Supports extremely large files by splitting them into chunks and processing them in parallel.
- **QR Code Connectivity**: Instantly connect your phone by scanning a dynamically generated QR code.
- **"Open in Browser" Mode**: One-click access to the full web-based file manager from your desktop.
- **Bulk Actions**: Select multiple files to download as a single ZIP archive or delete them in batches.

## 🛠️ Tech Stack

- **Frontend (Desktop)**: PyQt6 with Glassmorphism styling.
- **Frontend (Web)**: Vanilla JS, Semantic HTML5, CSS3 Variables.
- **Backend**: Flask with Gunicorn & Gevent for high-concurrency handling.
- **Compression**: Native Python `zipfile` with streaming support.

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Tirthmoradiya/file_transfer.git
   cd file_transfer
   ```

2. **Setup virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚦 Usage

### Desktop App (Recommended)
Launch the graphical interface to configure and monitor your server:
```bash
python main_gui.py
```
1. Select your **Uploads Directory**.
2. Customize **Advanced Settings** (Workers, Extensions, etc.).
3. Click **Start Server**.
4. Scan the QR code or click **Open in Browser** to manage files.

### Terminal Mode
For headless environments:
```bash
python run.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

This is a personal utility built for speed and convenience. If you encounter issues, please check the [Troubleshooting](DOCUMENTATION.md#troubleshooting) section in the documentation.
