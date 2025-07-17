from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import tempfile
import shutil
from pathlib import Path
from typing import List
import uuid
from pypdf import PdfWriter, PdfReader
from PIL import Image
import json
import asyncio
from pdf2image import convert_from_path
import base64
from io import BytesIO
import time
import threading
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Create directories
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("temp", exist_ok=True)

# Mount static files will be done after app creation

# Templates
templates = Jinja2Templates(directory="templates")

# In-memory storage for sessions (in production, use Redis or database)
sessions = {}

# Session cleanup configuration
SESSION_TIMEOUT = 60  # 1 minute for testing (change to 3600 for production)
CLEANUP_INTERVAL = 30   # 30 seconds for testing (change to 300 for production)

# Security configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
DEBUG_TOKEN = os.getenv("DEBUG_TOKEN", "your-secret-debug-token-here")

# Security dependencies
security = HTTPBearer()

def verify_debug_access(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify debug endpoint access"""
    if not DEBUG_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    
    if credentials.credentials != DEBUG_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid debug token")
    
    return credentials

# Background cleanup task
def cleanup_background_task():
    """Background task that runs cleanup periodically"""
    print("🧹 Background cleanup task started")
    while True:
        try:
            print(f"🔍 Running cleanup check... (Sessions: {len(sessions)})")
            SessionManager.cleanup_expired_sessions()
            time.sleep(CLEANUP_INTERVAL)
        except Exception as e:
            print(f"❌ Error in cleanup background task: {e}")
            time.sleep(CLEANUP_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    print("🚀 Starting PDF Editor Web App...")
    
    # Run initial cleanup of orphaned files from previous sessions
    print("🧹 Running initial cleanup of orphaned files...")
    orphaned_count = SessionManager.cleanup_orphaned_files()
    if orphaned_count > 0:
        print(f"🗑️  Cleaned up {orphaned_count} orphaned files from previous sessions")
    else:
        print("✅ No orphaned files found")
    
    # Start background cleanup task
    cleanup_thread = threading.Thread(target=cleanup_background_task, daemon=True)
    cleanup_thread.start()
    print(f"✅ Started background cleanup task (interval: {CLEANUP_INTERVAL}s, timeout: {SESSION_TIMEOUT}s)")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down PDF Editor...")

# Create FastAPI app with lifespan
app = FastAPI(title="PDF Editor Web App", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class SessionManager:
    @staticmethod
    def create_session(session_id: str):
        """Create a new session with timestamp"""
        sessions[session_id] = {
            "files": {},
            "order": [],
            "created_at": time.time(),
            "last_accessed": time.time(),
            "downloaded": False
        }
    
    @staticmethod
    def update_session_access(session_id: str):
        """Update last accessed time for session"""
        if session_id in sessions:
            sessions[session_id]["last_accessed"] = time.time()
    
    @staticmethod
    def cleanup_session(session_id: str):
        """Clean up all files and data for a session"""
        if session_id not in sessions:
            return
        
        try:
            # Delete all uploaded files
            upload_dir = Path(f"uploads/{session_id}")
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
            
            # Delete combined PDF
            combined_pdf = Path(f"temp/combined_{session_id}.pdf")
            if combined_pdf.exists():
                combined_pdf.unlink()
            
            # Remove from sessions
            del sessions[session_id]
            print(f"Cleaned up session: {session_id}")
            
        except Exception as e:
            print(f"Error cleaning up session {session_id}: {e}")
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions in memory and orphaned files on disk"""
        current_time = time.time()
        expired_sessions = []
        
        # Clean up expired sessions in memory
        for session_id, session_data in sessions.items():
            # Check if session has expired (1 hour of inactivity)
            if current_time - session_data["last_accessed"] > SESSION_TIMEOUT:
                expired_sessions.append(session_id)
            # Also clean up downloaded sessions after 10 minutes
            elif session_data.get("downloaded") and current_time - session_data["last_accessed"] > 600:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            SessionManager.cleanup_session(session_id)
        
        if expired_sessions:
            print(f"Cleaned up {len(expired_sessions)} expired sessions from memory")
        
        # Clean up orphaned files on disk
        orphaned_count = SessionManager.cleanup_orphaned_files()
        if orphaned_count > 0:
            print(f"Cleaned up {orphaned_count} orphaned files from disk")
    
    @staticmethod
    def cleanup_orphaned_files():
        """Clean up files on disk that aren't tracked in memory sessions"""
        orphaned_count = 0
        current_time = time.time()
        
        try:
            # Clean up orphaned upload directories
            uploads_dir = Path("uploads")
            if uploads_dir.exists():
                for session_dir in uploads_dir.iterdir():
                    if session_dir.is_dir():
                        session_id = session_dir.name
                        
                        # If session is not in memory, check if directory is old
                        if session_id not in sessions:
                            # Check directory modification time
                            dir_mtime = session_dir.stat().st_mtime
                            age = current_time - dir_mtime
                            
                            # Remove if older than session timeout
                            if age > SESSION_TIMEOUT:
                                try:
                                    shutil.rmtree(session_dir)
                                    orphaned_count += 1
                                    print(f"🗑️  Removed orphaned upload directory: {session_id}")
                                except Exception as e:
                                    print(f"❌ Error removing orphaned directory {session_id}: {e}")
            
            # Clean up orphaned combined PDFs
            temp_dir = Path("temp")
            if temp_dir.exists():
                for pdf_file in temp_dir.glob("combined_*.pdf"):
                    # Extract session ID from filename
                    filename = pdf_file.name
                    if filename.startswith("combined_") and filename.endswith(".pdf"):
                        session_id = filename[9:-4]  # Remove "combined_" and ".pdf"
                        
                        # If session is not in memory, check if file is old
                        if session_id not in sessions:
                            file_mtime = pdf_file.stat().st_mtime
                            age = current_time - file_mtime
                            
                            # Remove if older than session timeout
                            if age > SESSION_TIMEOUT:
                                try:
                                    pdf_file.unlink()
                                    orphaned_count += 1
                                    print(f"🗑️  Removed orphaned PDF: {filename}")
                                except Exception as e:
                                    print(f"❌ Error removing orphaned PDF {filename}: {e}")
        
        except Exception as e:
            print(f"❌ Error during orphaned file cleanup: {e}")
        
        return orphaned_count
    
    @staticmethod
    def get_filesystem_stats():
        """Get statistics about files on disk vs in memory"""
        stats = {
            "memory_sessions": len(sessions),
            "upload_directories": 0,
            "combined_pdfs": 0,
            "orphaned_uploads": 0,
            "orphaned_pdfs": 0,
            "total_upload_size_mb": 0,
            "total_pdf_size_mb": 0
        }
        
        try:
            # Count upload directories
            uploads_dir = Path("uploads")
            if uploads_dir.exists():
                upload_dirs = [d for d in uploads_dir.iterdir() if d.is_dir()]
                stats["upload_directories"] = len(upload_dirs)
                
                # Count orphaned upload directories
                for session_dir in upload_dirs:
                    session_id = session_dir.name
                    if session_id not in sessions:
                        stats["orphaned_uploads"] += 1
                    
                    # Calculate total size
                    try:
                        for file_path in session_dir.rglob("*"):
                            if file_path.is_file():
                                stats["total_upload_size_mb"] += file_path.stat().st_size
                    except:
                        pass
            
            # Count combined PDFs
            temp_dir = Path("temp")
            if temp_dir.exists():
                pdf_files = list(temp_dir.glob("combined_*.pdf"))
                stats["combined_pdfs"] = len(pdf_files)
                
                # Count orphaned PDFs and calculate size
                for pdf_file in pdf_files:
                    filename = pdf_file.name
                    if filename.startswith("combined_") and filename.endswith(".pdf"):
                        session_id = filename[9:-4]
                        if session_id not in sessions:
                            stats["orphaned_pdfs"] += 1
                    
                    try:
                        stats["total_pdf_size_mb"] += pdf_file.stat().st_size
                    except:
                        pass
            
            # Convert bytes to MB
            stats["total_upload_size_mb"] = round(stats["total_upload_size_mb"] / (1024 * 1024), 2)
            stats["total_pdf_size_mb"] = round(stats["total_pdf_size_mb"] / (1024 * 1024), 2)
        
        except Exception as e:
            print(f"❌ Error getting filesystem stats: {e}")
        
        return stats

class FileManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.upload_dir = Path(f"uploads/{session_id}")
        self.upload_dir.mkdir(exist_ok=True)
        
    def save_file(self, file: UploadFile) -> dict:
        """Save uploaded file and return file info"""
        file_id = str(uuid.uuid4())
        file_path = self.upload_dir / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Generate thumbnail
        thumbnail = self.generate_thumbnail(file_path)
        
        return {
            "id": file_id,
            "filename": file.filename,
            "path": str(file_path),
            "type": "pdf" if file.filename.lower().endswith('.pdf') else "image",
            "thumbnail": thumbnail
        }
    
    def generate_thumbnail(self, file_path: Path) -> str:
        """Generate base64 thumbnail for file"""
        try:
            if str(file_path).lower().endswith('.pdf'):
                # PDF thumbnail - try with poppler, fallback to default icon
                try:
                    pages = convert_from_path(file_path, first_page=1, last_page=1, dpi=50)
                    if pages:
                        img = pages[0]
                        img.thumbnail((120, 120), Image.Resampling.LANCZOS)
                        buffer = BytesIO()
                        img.save(buffer, format='PNG')
                        return base64.b64encode(buffer.getvalue()).decode()
                except Exception as pdf_error:
                    print(f"PDF thumbnail generation failed (poppler may not be installed): {pdf_error}")
                    # Return empty string to use default PDF icon
                    return ""
            else:
                # Image thumbnail
                with Image.open(file_path) as img:
                    img.thumbnail((120, 120), Image.Resampling.LANCZOS)
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return ""
    
    def combine_files(self, file_order: List[str]) -> str:
        """Combine files in specified order"""
        output_path = Path(f"temp/combined_{self.session_id}.pdf")
        
        pdf_writer = PdfWriter()
        temp_files = []
        
        try:
            for file_id in file_order:
                file_info = sessions[self.session_id]["files"].get(file_id)
                if not file_info:
                    continue
                    
                file_path = Path(file_info["path"])
                
                if file_info["type"] == "pdf":
                    # Handle PDF
                    pdf_reader = PdfReader(file_path)
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
                else:
                    # Handle image - convert to PDF first
                    temp_pdf = self.image_to_pdf(file_path)
                    if temp_pdf:
                        temp_files.append(temp_pdf)
                        pdf_reader = PdfReader(temp_pdf)
                        for page in pdf_reader.pages:
                            pdf_writer.add_page(page)
            
            # Write combined PDF
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error combining files: {e}")
            return None
    
    def image_to_pdf(self, image_path: Path) -> str:
        """Convert image to PDF"""
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_pdf.close()
                
                img.save(temp_pdf.name, "PDF", resolution=100.0)
                return temp_pdf.name
        except Exception as e:
            print(f"Error converting image to PDF: {e}")
            return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...), session_id: str = Form(...)):
    """Upload multiple files"""
    if session_id not in sessions:
        SessionManager.create_session(session_id)
    
    SessionManager.update_session_access(session_id)
    
    file_manager = FileManager(session_id)
    uploaded_files = []
    
    for file in files:
        if file.filename:
            file_info = file_manager.save_file(file)
            sessions[session_id]["files"][file_info["id"]] = file_info
            sessions[session_id]["order"].append(file_info["id"])
            uploaded_files.append(file_info)
    
    return {"files": uploaded_files}

@app.post("/reorder")
async def reorder_files(session_id: str = Form(...), order: str = Form(...)):
    """Reorder files"""
    if session_id not in sessions:
        return {"error": "Session not found"}
    
    SessionManager.update_session_access(session_id)
    
    try:
        new_order = json.loads(order)
        sessions[session_id]["order"] = new_order
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

@app.post("/remove")
async def remove_file(session_id: str = Form(...), file_id: str = Form(...)):
    """Remove a file"""
    if session_id not in sessions:
        return {"error": "Session not found"}
    
    SessionManager.update_session_access(session_id)
    
    try:
        # Remove from files dict
        if file_id in sessions[session_id]["files"]:
            file_info = sessions[session_id]["files"][file_id]
            # Delete physical file
            try:
                os.unlink(file_info["path"])
            except:
                pass
            del sessions[session_id]["files"][file_id]
        
        # Remove from order
        if file_id in sessions[session_id]["order"]:
            sessions[session_id]["order"].remove(file_id)
        
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

@app.post("/combine")
async def combine_pdf(session_id: str = Form(...)):
    """Combine files into PDF"""
    if session_id not in sessions:
        return {"error": "Session not found"}
    
    SessionManager.update_session_access(session_id)
    
    file_manager = FileManager(session_id)
    output_path = file_manager.combine_files(sessions[session_id]["order"])
    
    if output_path:
        return {"download_url": f"/download/{session_id}"}
    else:
        return {"error": "Failed to combine files"}

@app.get("/download/{session_id}")
async def download_pdf(session_id: str):
    """Download combined PDF"""
    file_path = Path(f"temp/combined_{session_id}.pdf")
    if file_path.exists():
        # Mark session as downloaded for faster cleanup
        if session_id in sessions:
            sessions[session_id]["downloaded"] = True
            sessions[session_id]["last_accessed"] = time.time()
        
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename="combined.pdf"
        )
    return {"error": "File not found"}

@app.get("/files/{session_id}")
async def get_files(session_id: str):
    """Get files for session"""
    if session_id not in sessions:
        return {"files": [], "order": []}
    
    SessionManager.update_session_access(session_id)
    
    session_data = sessions[session_id]
    ordered_files = []
    
    for file_id in session_data["order"]:
        if file_id in session_data["files"]:
            ordered_files.append(session_data["files"][file_id])
    
    return {"files": ordered_files}

# Secured Debug endpoints for testing session management
@app.get("/debug/sessions")
async def debug_sessions(auth: HTTPAuthorizationCredentials = Depends(verify_debug_access)):
    """Debug endpoint to view all sessions - REQUIRES AUTHENTICATION"""
    current_time = time.time()
    session_info = {}
    
    for session_id, session_data in sessions.items():
        age = current_time - session_data["created_at"]
        inactive = current_time - session_data["last_accessed"]
        
        # Sanitize session IDs for security
        sanitized_id = session_id[:8] + "..." if len(session_id) > 8 else session_id
        
        session_info[sanitized_id] = {
            "files_count": len(session_data["files"]),
            "created_ago_seconds": int(age),
            "inactive_seconds": int(inactive),
            "downloaded": session_data.get("downloaded", False),
            "expires_in_seconds": int(SESSION_TIMEOUT - inactive) if inactive < SESSION_TIMEOUT else 0
        }
    
    return {
        "total_sessions": len(sessions),
        "session_timeout": SESSION_TIMEOUT,
        "cleanup_interval": CLEANUP_INTERVAL,
        "debug_mode": DEBUG_MODE,
        "sessions": session_info
    }

@app.post("/debug/cleanup")
async def debug_cleanup(auth: HTTPAuthorizationCredentials = Depends(verify_debug_access)):
    """Debug endpoint to manually trigger cleanup - REQUIRES AUTHENTICATION"""
    SessionManager.cleanup_expired_sessions()
    return {"message": "Cleanup triggered", "remaining_sessions": len(sessions)}

@app.post("/debug/cleanup-session/{session_id}")
async def debug_cleanup_session(session_id: str, auth: HTTPAuthorizationCredentials = Depends(verify_debug_access)):
    """Debug endpoint to manually cleanup a specific session - REQUIRES AUTHENTICATION"""
    if session_id in sessions:
        SessionManager.cleanup_session(session_id)
        return {"message": f"Session {session_id[:8]}... cleaned up"}
    return {"error": "Session not found"}

@app.get("/debug/filesystem")
async def debug_filesystem(auth: HTTPAuthorizationCredentials = Depends(verify_debug_access)):
    """Debug endpoint to view filesystem statistics - REQUIRES AUTHENTICATION"""
    stats = SessionManager.get_filesystem_stats()
    return {
        "filesystem_stats": stats,
        "cleanup_info": {
            "session_timeout": SESSION_TIMEOUT,
            "cleanup_interval": CLEANUP_INTERVAL,
            "debug_mode": DEBUG_MODE,
            "orphaned_files_detected": stats["orphaned_uploads"] + stats["orphaned_pdfs"]
        }
    }

@app.post("/debug/cleanup-orphaned")
async def debug_cleanup_orphaned(auth: HTTPAuthorizationCredentials = Depends(verify_debug_access)):
    """Debug endpoint to manually trigger orphaned file cleanup - REQUIRES AUTHENTICATION"""
    orphaned_count = SessionManager.cleanup_orphaned_files()
    return {
        "message": "Orphaned file cleanup triggered",
        "files_cleaned": orphaned_count,
        "remaining_stats": SessionManager.get_filesystem_stats()
    }

# Note: Background cleanup task is now handled by the lifespan event handler above

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)