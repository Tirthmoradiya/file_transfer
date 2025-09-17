# Parallel File Transfer

A modern, high-performance file sharing application built with Flask that supports chunked uploads, parallel processing, and QR code sharing for easy mobile access.

## Features

- **Chunked Upload**: Large files are split into chunks for reliable uploads
- **Parallel Processing**: Multiple chunks uploaded simultaneously for faster transfers
- **Drag & Drop Interface**: Modern, intuitive web interface
- **QR Code Sharing**: Automatically generates QR codes for easy mobile access
- **Bulk Download**: Select multiple files and download as ZIP
- **Network Discovery**: Automatically detects local IP for network sharing
- **Production Ready**: Uses Gunicorn with Gevent for high performance

## Screenshots

The application provides a clean, modern interface for file sharing with drag-and-drop functionality and progress tracking.

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd file-transfer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
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
- **Concurrency**: Parallel chunk processing (4 workers default)
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

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Troubleshooting

### Common Issues

**Port already in use**: Change the `SERVER_PORT` in `run.py`

**Permission errors**: Ensure the application has write permissions for `uploads/` and `temp/` directories

**Large file uploads**: Adjust `CHUNK_SIZE` and `PARALLEL_UPLOADS` based on your network conditions

**Network access issues**: Check firewall settings and ensure the server IP is accessible from client devices

## Support

For issues and questions, please open an issue on GitHub.
