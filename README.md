# PDF Editor - Web & Desktop Application

A modern PDF editor that allows you to combine multiple PDFs and images into a single document. Available as both a desktop application (tkinter) and a web application (FastAPI).

## 🚀 Features

### Core Functionality
- **Combine PDFs and Images** - Merge multiple PDF files and images (PNG, JPG, JPEG, GIF, BMP, TIFF) into one PDF
- **Drag & Drop Interface** - Intuitive file reordering with smooth animations
- **Real-time Thumbnails** - Preview PDF pages and images before combining
- **Session Management** - Automatic cleanup of temporary files
- **Responsive Design** - Works on desktop and mobile devices

### Desktop Application (tkinter)
- Native desktop interface with drag-and-drop reordering
- Smooth animations and visual feedback
- File thumbnails with PDF preview support
- Cross-platform compatibility (Windows, Mac, Linux)

### Web Application (FastAPI)
- Modern web interface with drag-and-drop functionality
- Session-based file management with automatic cleanup
- RESTful API for programmatic access
- Production-ready with security features

## 📋 Requirements

### Python Dependencies
```
pypdf==3.17.4
Pillow==10.1.0
pdf2image==1.17.0
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
jinja2==3.1.2
aiofiles==24.1.0
```

### System Dependencies
- **For PDF thumbnails (optional)**: Poppler
  - Windows: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
  - Mac: `brew install poppler`
  - Linux: `sudo apt-get install poppler-utils`

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pdf-editor
   ```

2. **Install Python dependencies**
   ```bash
   # For desktop app
   pip install -r requirements.txt
   
   # For web app
   pip install -r web_requirements.txt
   ```

3. **Install Poppler (optional, for PDF thumbnails)**
   - Follow system-specific instructions above
   - App works without poppler but won't show PDF previews

## 🖥️ Usage

### Desktop Application
```bash
python pdf_editor.py
```

**Features:**
- Drag files from your computer to add them
- Drag file cards to reorder them
- Click × to remove files
- Click "Combine PDF" to create final document

### Web Application
```bash
python web_app.py
```

Then open http://localhost:8000 in your browser.

**Features:**
- Drag & drop files to upload
- Drag file cards to reorder
- Automatic session cleanup
- Download combined PDF

## 🔧 Configuration

### Web Application Settings

#### Session Management
```python
# In web_app.py
SESSION_TIMEOUT = 3600  # 1 hour (production)
CLEANUP_INTERVAL = 300   # 5 minutes (production)

# For testing
SESSION_TIMEOUT = 60    # 1 minute
CLEANUP_INTERVAL = 30   # 30 seconds
```

#### Debug Mode (Development Only)
```bash
# Enable debug endpoints
export DEBUG_MODE=true
export DEBUG_TOKEN=your-secret-token-here

# Production (default) - debug endpoints disabled
# Don't set DEBUG_MODE or set to false
```

## 🔒 Security

### Debug Endpoints
Debug endpoints are **disabled by default** for security:

- **Production**: Debug endpoints return 404
- **Development**: Require authentication with bearer token
- **Data sanitization**: Session IDs truncated, no sensitive paths exposed

#### Accessing Debug Endpoints (Development Only)
```bash
# Set environment variables
export DEBUG_MODE=true
export DEBUG_TOKEN=my-secret-token

# Access with authentication
curl -H "Authorization: Bearer my-secret-token" \
     http://localhost:8000/debug/sessions
```

### Available Debug Endpoints
- `GET /debug/sessions` - View active sessions
- `POST /debug/cleanup` - Trigger manual cleanup
- `GET /debug/filesystem` - View filesystem statistics
- `POST /debug/cleanup-orphaned` - Clean orphaned files
- `POST /debug/cleanup-session/{id}` - Clean specific session

## 🧪 Testing

### Comprehensive Test Suite
```bash
# Run full test suite
python test_session_cleanup.py

# Quick cleanup test
python quick_cleanup_test.py
```

### Manual Testing
```bash
# Test server connection
curl http://localhost:8000

# Upload files (replace with actual files)
curl -X POST "http://localhost:8000/upload" \
  -F "files=@test.pdf" \
  -F "session_id=test123"

# View sessions (requires debug mode)
curl -H "Authorization: Bearer your-token" \
     http://localhost:8000/debug/sessions
```

## 📁 Project Structure

```
pdf-editor/
├── pdf_editor.py              # Desktop application
├── web_app.py                 # Web application
├── requirements.txt           # Desktop app dependencies
├── web_requirements.txt       # Web app dependencies
├── test_session_cleanup.py    # Comprehensive tests
├── quick_cleanup_test.py      # Quick test script
├── static/
│   ├── style.css             # Web app styles
│   └── script.js             # Web app JavaScript
├── templates/
│   └── index.html            # Web app template
├── uploads/                  # User uploaded files (auto-created)
├── temp/                     # Combined PDFs (auto-created)
└── README.md                 # This file
```

## 🔄 Session Management & Cleanup

The web application includes comprehensive session management:

### Automatic Cleanup
- **Active sessions**: Cleaned after 1 hour of inactivity
- **Downloaded sessions**: Cleaned after 10 minutes
- **Orphaned files**: Cleaned on server restart
- **Background task**: Runs cleanup every 5 minutes

### File Lifecycle
1. **Upload** → Files stored in `uploads/{session_id}/`
2. **Combine** → PDF created in `temp/combined_{session_id}.pdf`
3. **Download** → Session marked as downloaded
4. **Cleanup** → All files deleted automatically

## 🚀 Production Deployment

### Environment Variables
```bash
# Required for production
DEBUG_MODE=false              # Disable debug endpoints
SESSION_TIMEOUT=3600          # 1 hour session timeout
CLEANUP_INTERVAL=300          # 5 minute cleanup interval

# Optional
DEBUG_TOKEN=secret-token      # Only if DEBUG_MODE=true
```

### Docker Example
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -r web_requirements.txt

# Install poppler for PDF thumbnails (optional)
RUN apt-get update && apt-get install -y poppler-utils

EXPOSE 8000

CMD ["python", "web_app.py"]
```

### Reverse Proxy (nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🐛 Troubleshooting

### Common Issues

**1. PDF thumbnails not showing**
- Install poppler system dependency
- App works without poppler but shows default icons

**2. Files not being cleaned up**
- Check server logs for cleanup messages
- Verify session timeout settings
- Use debug endpoints to monitor sessions

**3. Debug endpoints return 404**
- This is normal in production (security feature)
- Set `DEBUG_MODE=true` for development only

**4. Upload fails**
- Check file size limits
- Verify supported file types
- Check server logs for errors

### Logs to Monitor
```bash
# Server startup
🚀 Starting PDF Editor Web App...
✅ Started background cleanup task

# Cleanup activity
🔍 Running cleanup check... (Sessions: 2)
🗑️ Cleaned up 1 expired sessions from memory
🗑️ Removed orphaned upload directory: session_123
```

## 📝 API Documentation

### Upload Files
```bash
POST /upload
Content-Type: multipart/form-data

files: [file1, file2, ...]
session_id: string
```

### Reorder Files
```bash
POST /reorder
Content-Type: application/x-www-form-urlencoded

session_id: string
order: ["file_id1", "file_id2", ...]
```

### Combine Files
```bash
POST /combine
Content-Type: application/x-www-form-urlencoded

session_id: string
```

### Download PDF
```bash
GET /download/{session_id}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [pypdf](https://pypdf.readthedocs.io/) - PDF manipulation
- [Pillow](https://pillow.readthedocs.io/) - Image processing
- [pdf2image](https://github.com/Belval/pdf2image) - PDF to image conversion

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review server logs
3. Test with debug endpoints (development only)
4. Open an issue on GitHub

---

**Made with ❤️ for easy PDF management**