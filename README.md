# My Personal File Transfer

This is a personal file sharing tool I built for myself. It runs on my local network, supports large uploads with chunking and parallel transfers, and gives me a simple drag‑and‑drop UI. I also added a QR code so I can quickly open it on my phone when I need to move files between devices.

## Features

- **Chunked Upload**: Large files are split into chunks for reliable uploads
- **Parallel Processing**: Multiple chunks uploaded simultaneously for faster transfers
- **Drag & Drop Interface**: Modern, intuitive web interface
- **QR Code Sharing**: Automatically generates QR codes for easy mobile access
- **Bulk Download**: Select multiple files and download as ZIP
- **Network Discovery**: Automatically detects local IP for network sharing
- **Production Ready**: Uses Gunicorn with Gevent for high performance

## Why I built this

- I needed a quick way to move files between my laptop and phone on the same Wi‑Fi.
- Cloud drives are overkill for quick transfers and sometimes slow.
- I wanted control over file size limits, formats, and basic access protection on my LAN.

## Installation (for my setup)

0. uploads/ and temp/ folders are ignored for safety and these folders are auto-created on first run. If you prefer, create them manually:
```bash
mkdir uploads temp
```

1. Clone the repository:
```bash
git clone https://github.com/Tirthmoradiya/file_transfer.git
cd file_transfer
```

2. Create a virtual environment if you want to use otherwise you can skip this step:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```
### Optional authentication
Server:
```bash
export AUTH_TOKEN="your-secret"
python run.py
```
Client (browser console):
```javascript
localStorage.setItem('AUTH_TOKEN', 'your-secret');
```

## Usage

### Quick Start

Run the application:
```bash
python run.py
```

The server will start and display:
- Local network URL for access from other devices
- QR code for easy mobile access
- Server status information

## Performance & Transfer Speed

This runs on my local network, so speed is mostly limited by Wi‑Fi/Ethernet and device disk speeds.

- On Wi‑Fi 5 (AC): I usually see ~30–60 MB/s (240–560 Mbps)
- On Wi‑Fi 6 (AX): ~60–120 MB/s (480–960 Mbps) when close to the router
- On Gigabit Ethernet: up to ~110–115 MB/s (≈ 940 Mbps) end‑to‑end

What affects speed:
- Network quality (signal strength, interference, router bandwidth)
- Client/server disk speed (SSD vs HDD, mobile storage speed)
- CPU on both sides (ZIP downloads are CPU+I/O bound)
- Settings like `CHUNK_SIZE` and `PARALLEL_UPLOADS` (for uploads)

How I measure it quickly:
1. Upload or download a large file (e.g., 2–5 GB)
2. Note the start and end time
3. Speed ≈ file_size_bytes / elapsed_seconds

Tuning tips I use:
- Set `PARALLEL_UPLOADS` to 2–4 for faster uploads on stable networks (I sometimes set it to 1 for simplicity)
- Keep `CHUNK_SIZE` between 5–16 MB (5 MB works well across devices)
- Use Ethernet for the server if possible; keep the client close to the router
- Avoid running heavy CPU tasks while creating large ZIPs

Note: Single‑file downloads are streamed directly and support resume. Multi‑file ZIP downloads are generated on the fly; resume after stopping mid‑download isn’t kept across requests unless I add a persistent ZIP cache.

### Features Overview

#### File Upload
- Drag and drop files onto the upload zone
- Click to select files manually
- Real-time progress tracking
- Automatic chunking for large files
- Parallel upload processing

#### File Management
- View all uploaded files
- Individual file downloads
- Bulk selection and ZIP download
- Automatic file listing refresh

#### Network Sharing
- Accessible from any device on the local network
- QR code generation for mobile devices
- Automatic IP detection

## Technical Details

### Architecture
- **Backend**: Flask with Gunicorn and Gevent
- **Frontend**: Vanilla JavaScript with modern async/await
- **Upload Strategy**: Chunked uploads with configurable chunk size (5MB default)
- **Concurrency**: Parallel chunk processing (1 workers default)
- **File Storage**: Local filesystem with organized directory structure

### Configuration

Key settings in the application:

```python
CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB chunks
PARALLEL_UPLOADS = 4          # Concurrent upload workers
SERVER_PORT = 5000           # Default server port
```

### API Endpoints

- `GET /` - Main application interface
- `POST /upload-chunk` - Chunked file upload
- `POST /download-zip` - Multi-file ZIP download
- `GET /uploads/<filename>` - Individual file download

## Development

### Project Structure
```
file-transfer/
├── app.py              # Main Flask application
├── run.py              # Server startup and configuration
├── templates/
│   └── index.html      # Web interface
├── uploads/            # Uploaded files (auto-created)
├── temp/              # Temporary chunk storage (auto-created)
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

### Running in Development

For development with auto-reload:
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

### Production Deployment

The application is production-ready with Gunicorn:
```bash
python run.py
```

## Dependencies

- **Flask**: Web framework
- **Gunicorn**: WSGI HTTP Server
- **Gevent**: Asynchronous networking library
- **QRCode**: QR code generation
- **Pillow**: Image processing for QR codes

## Contributing

This is a personal project I use for myself. I’m not looking for external contributions right now. If you find it useful, feel free to fork your own copy and adapt it.

## License

This repository is public for reference. If I include a license file, it will be MIT; otherwise, assume it’s for personal use only.

## Troubleshooting

### Common Issues

**Port already in use**: Change the `SERVER_PORT` in `run.py`

**Permission errors**: Ensure the application has write permissions for `uploads/` and `temp/` directories

**Large file uploads**: Adjust `CHUNK_SIZE` and `PARALLEL_UPLOADS` based on your network conditions

**Network access issues**: Check firewall settings and ensure the server IP is accessible from client devices

## Support

This is something I built for my own needs, so I don’t provide support. If you have ideas or need changes, please fork it and modify as you like.
