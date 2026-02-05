from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sse_starlette.sse import EventSourceResponse
import yt_dlp
import os
import asyncio
import uuid
from pathlib import Path
from typing import Dict
from datetime import datetime
import logging
import shutil
import threading
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import glob
import shutil

app = FastAPI(title="YouTube Downloader API")


# Enable CORS for your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)


# Create downloads directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


# Use threading.Lock for progress_hook (called from yt-dlp thread)
# Use asyncio.Lock for async endpoint access
progress_thread_lock = threading.Lock()
progress_async_lock = asyncio.Lock()
download_progress: Dict[str, dict] = {}


class VideoRequest(BaseModel):
    url: HttpUrl
    format: str = "best"
    output_format: str = "original"


class DownloadJob(BaseModel):
    job_id: str
    status: str
    message: str


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@app.get("/api/status")
def read_root():
    return {"message": "YouTube Downloader API", "status": "running"}


@app.post("/api/get-video-info")
async def get_video_info(request: VideoRequest):
    try: 
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(str(request.url), download=False)

            formats_dict = {}  # Use dict to deduplicate by resolution
            
            if video_info.get('formats'):
                for f in video_info['formats']:
                    height = f.get('height')
                    
                    # Skip formats without height (audio-only, etc.)
                    if height is None or not isinstance(height, (int, float)):
                        continue
                    
                    resolution = f'{int(height)}p'
                    filesize = f.get('filesize') or 0  # Handle None filesize
                    
                    # Deduplicate: prefer formats with known filesize
                    if resolution not in formats_dict:
                        formats_dict[resolution] = {
                            'format_id': f['format_id'],
                            'resolution': resolution,
                            'ext': f.get('ext', 'unknown'),
                            'filesize': filesize,
                            'has_filesize': filesize > 0
                        }
                    elif filesize > 0 and formats_dict[resolution].get('filesize', 0) == 0:
                        # Replace format with no filesize with one that has size
                        formats_dict[resolution] = {
                            'format_id': f['format_id'],
                            'resolution': resolution,
                            'ext': f.get('ext', 'unknown'),
                            'filesize': filesize,
                            'has_filesize': True
                        }
            
            # Convert to list and sort safely
            formats = sorted(
                formats_dict.values(), 
                key=lambda x: int(x['resolution'].replace('p', '')),
                reverse=True
            )
            
            return {
                "title": video_info.get('title', 'Unknown'),
                "duration": video_info.get('duration', 0),
                "thumbnail": video_info.get('thumbnail', ''),
                "uploader": video_info.get('uploader', 'Unknown'),
                "formats": formats
            }
            
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch video info: {str(e)}")


def progress_hook(d: dict, job_id: str):
    """Called from yt-dlp thread - use thread-safe update"""
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        percentage = (downloaded / total * 100) if total > 0 else 0
        
        # Use threading.Lock since this is called from a thread pool
        with progress_thread_lock:
            download_progress[job_id] = {
                'status': 'downloading',
                'percentage': round(percentage, 2),
                'downloaded': downloaded,
                'total': total,
                'speed': d.get('speed', 0),
                'eta': d.get('eta', 0),
                'filename': d.get('filename', ''),
                'timestamp': datetime.now().isoformat()
            }
        
    elif d['status'] == 'finished':
        with progress_thread_lock:
            download_progress[job_id] = {
                'status': 'processing',
                'percentage': 100,
                'message': 'Processing file...',
                'filename': d.get('filename', ''),
                'timestamp': datetime.now().isoformat()
            }


async def download_video_task(url: str, format_type: str, job_id: str, output_format: str = "original"):
    """Background task to download video with progress tracking"""
    try:
        with progress_thread_lock:
            download_progress[job_id] = {
                'status': 'starting',
                'percentage': 0,
                'message': 'Initializing download...',
                'timestamp': datetime.now().isoformat()
            }
        
        ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'format': get_format_selector(format_type, output_format),
            'outtmpl': str(DOWNLOAD_DIR / f'{job_id}_%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: progress_hook(d, job_id)],
            'writethumbnail': False,
            'keepvideo': False,
            'max_filesize': 5 * 1024 * 1024 * 1024,
            'socket_timeout': 30,
        }
        
        # Handle different format types
        if format_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif output_format == 'mp4':
            # For MP4: must convert audio to AAC if not compatible
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['postprocessor_args'] = {
                # Copy video, convert audio to AAC (MP4-compatible)
                'ffmpeg': ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k']
            }
        elif output_format == 'webm':
            # For WebM: can safely copy most codecs
            ydl_opts['merge_output_format'] = 'webm'
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': ['-c:v', 'copy', '-c:a', 'copy']
            }
        # For 'original': no merge_output_format, let yt-dlp decide
        
        # Run yt-dlp in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: download_with_ytdlp(ydl_opts, url, job_id, output_format))

    except yt_dlp.utils.DownloadError as de:
        logger.error(f"Download error for job {job_id}: {str(de)}")
        with progress_thread_lock:
            download_progress[job_id] = {
                'status': 'error',
                'percentage': 0,
                'message': 'Video unavailable or restricted',
                'error_type': 'download_error',
                'timestamp': datetime.now().isoformat()
            }    
    except Exception as e:
        logger.error(f"Unexpected error in job {job_id}: {str(e)}")
        with progress_thread_lock:
            download_progress[job_id] = {
                'status': 'error',
                'percentage': 0,
                'message': str(e),
                'error_type': 'unknown_error',
                'timestamp': datetime.now().isoformat()
            }

def download_with_ytdlp(ydl_opts: dict, url: str, job_id: str, output_format: str = "original"):
    """Synchronous download function"""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        # Determine final filename based on processing
        if any(pp.get('key') == 'FFmpegExtractAudio' for pp in ydl_opts.get('postprocessors', [])):
            # Audio extraction becomes .mp3
            filename = filename.rsplit('.', 1)[0] + '.mp3'
        elif ydl_opts.get('merge_output_format'):
            # Explicit format conversion
            filename = filename.rsplit('.', 1)[0] + '.' + ydl_opts['merge_output_format']
        # For 'original': keep native extension (no modification)
        
        with progress_thread_lock:
            download_progress[job_id]['status'] = 'completed'
            download_progress[job_id]['filename'] = filename
            download_progress[job_id]['percentage'] = 100
            download_progress[job_id]['message'] = 'Download completed!'


@app.post("/api/download/start", response_model=DownloadJob)
async def start_download(request: VideoRequest, background_tasks: BackgroundTasks):
    """Start a download job and return job ID"""
    # Check disk space BEFORE creating job
    stat = shutil.disk_usage(DOWNLOAD_DIR)
    if stat.free < 5 * 1024 * 1024 * 1024:  # 5GB free space check
        raise HTTPException(status_code=507, detail="Insufficient disk space to start download")
    
    job_id = str(uuid.uuid4())
    
    # Start download in background
    background_tasks.add_task(
        download_video_task, 
        str(request.url), 
        request.format, 
        job_id,
        request.output_format
    )
    
    return DownloadJob(
        job_id=job_id,
        status="queued",
        message="Download queued"
    )


@app.get("/api/download/progress/{job_id}")
async def progress_stream(job_id: str):
    """Server-Sent Events endpoint for real-time progress updates"""
    async def event_generator():
        while True:
            # Use asyncio lock for async context
            async with progress_async_lock:
                if job_id in download_progress:
                    progress = download_progress[job_id].copy()
                else:
                    progress = {'status': 'waiting', 'message': 'Waiting for job to start...'}
            
            yield {
                "event": "progress",
                "data": str(progress)
            }
            
            if progress.get('status') in ['completed', 'error']:
                yield {"event": "close", "data": "Stream closed"}
                break
            
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())


@app.get("/api/download/status/{job_id}")
async def get_download_status(job_id: str):
    """Get current status of a download job"""
    async with progress_async_lock:
        if job_id not in download_progress:
            raise HTTPException(status_code=404, detail="Job not found")
        return download_progress[job_id].copy()


async def delayed_cleanup(job_id: str, delay: int):
    """Clean up file and progress data after delay"""
    await asyncio.sleep(delay)
    async with progress_async_lock:
        if job_id in download_progress:
            filename = download_progress[job_id].get('filename')
            if filename and os.path.exists(filename):
                try:
                    os.remove(filename)
                    logger.info(f"Auto-deleted file for job {job_id}: {filename}")
                except Exception as e:
                    logger.error(f"Failed to delete file {filename}: {str(e)}")
            del download_progress[job_id]


@app.get("/api/download/file/{job_id}")
async def download_file(job_id: str, background_tasks: BackgroundTasks):
    """Download the completed file"""
    async with progress_async_lock:
        if job_id not in download_progress:
            raise HTTPException(status_code=404, detail="Job not found")
        
        progress = download_progress[job_id].copy()
    
    if progress['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Download not completed yet")
    
    filename = progress.get('filename')
    if not filename or not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Auto-cleanup after 5 minutes
    background_tasks.add_task(delayed_cleanup, job_id, delay=300)
    
    return FileResponse(
        path=filename,
        filename=os.path.basename(filename),
        media_type='application/octet-stream'
    )


@app.delete("/api/download/{job_id}")
async def cleanup_download(job_id: str):
    """Clean up downloaded file and job data"""
    async with progress_async_lock:
        if job_id not in download_progress:
            raise HTTPException(status_code=404, detail="Job not found")
        
        progress = download_progress[job_id]
        filename = progress.get('filename')
        
        # Delete file if exists
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
                logger.info(f"Manually deleted file for job {job_id}: {filename}")
            except Exception as e:
                logger.error(f"Failed to delete file {filename}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
        
        # Remove from progress tracking
        del download_progress[job_id]
        
        return {"message": "Cleanup successful"}

def cleanup_downloads_folder():
    """Clean all files from downloads folder"""
    try:
        deleted_count = 0
        total_size = 0
        
        for item in DOWNLOAD_DIR.iterdir():
            try:
                if item.is_file():
                    file_size = item.stat().st_size
                    item.unlink()
                    deleted_count += 1
                    total_size += file_size
                elif item.is_dir():
                    shutil.rmtree(item)
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete {item}: {str(e)}")
        
        if deleted_count > 0:
            logger.info(f"Cleanup: Deleted {deleted_count} items, freed {total_size / (1024 * 1024):.2f} MB")
            
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")

# Add startup event
@app.on_event("startup")
async def startup_event():
    """Clean downloads folder on server start"""
    logger.info("=== Server Starting ===")
    cleanup_downloads_folder()
    logger.info("=== Server Ready ===")

# Add shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean downloads folder on server shutdown"""
    logger.info("=== Server Shutting Down ===")
    cleanup_downloads_folder()
    logger.info("=== Cleanup Complete ===")

def get_format_selector(format_type: str, output_format: str = "original") -> str:
    """Select format string for yt-dlp based on requirements"""

    # Common format map for all output types
    # Use simple bestvideo+bestaudio pattern for reliability
    format_map = {
        'best': 'bestvideo+bestaudio/best',
        '2160p': 'bestvideo[height<=2160]+bestaudio/best',
        '1440p': 'bestvideo[height<=1440]+bestaudio/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best',
        '720p': 'bestvideo[height<=720]+bestaudio/best',
        '480p': 'bestvideo[height<=480]+bestaudio/best',
        '360p': 'bestvideo[height<=360]+bestaudio/best',
        '240p': 'bestvideo[height<=240]+bestaudio/best',
        '144p': 'bestvideo[height<=144]+bestaudio/best',
    }
    
    return format_map.get(format_type, format_map['best'])

# Custom StaticFiles to handle SPA routing
class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except Exception as ex:
            # If file not found, return index.html for SPA routing
            if hasattr(ex, 'status_code') and ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex

# Serve React/Vite static files (only in production/Docker)
frontend_build_path = Path(__file__).parent / "frontend" / "build"
if frontend_build_path.exists():
    # Vite puts assets in 'assets' folder, not 'static'
    assets_path = frontend_build_path / "assets"
    
    if assets_path.exists():
        # Mount Vite assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    
    # Serve React app for all other routes (SPA routing)
    # This must be last to catch all non-API routes
    app.mount("/", SPAStaticFiles(directory=str(frontend_build_path), html=True), name="spa")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
