# YouTube Downloader

A modern YouTube video downloader built with FastAPI (backend) and React (frontend) with real-time download progress tracking.

## Features

- 🎥 Download YouTube videos in multiple qualities (144p to 4K)
- 🎵 Extract audio from videos (MP3 format)
- 📊 Real-time download progress updates using Server-Sent Events (SSE)
- 🔄 Multiple output formats: MP4, WebM, or original
- 🚀 Fast and efficient video processing with FFmpeg
- 🎨 Modern, responsive React UI with Tailwind CSS
- 📦 Single container Docker deployment
- 🧹 Automatic file cleanup (after 5 minutes of download)
- 💾 Download history and status tracking

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **yt-dlp** - YouTube video downloader (fork of youtube-dl)
- **FFmpeg** - Video/audio processing and format conversion
- **Uvicorn** - ASGI server
- **SSE Starlette** - Server-Sent Events support
- **Pydantic** - Data validation

### Frontend
- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Radix UI** - Headless UI components
- **Lucide React** - Icon library

## Prerequisites

### Docker Deployment
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Download from: https://www.docker.com/products/docker-desktop/

### Local Development
- Python 3.11+
- Node.js 18+
- npm or yarn

## Docker Deployment

### Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd youtube-downloader
```

2. Build and run with Docker Compose:
```bash
docker-compose up -d --build
```

3. Access the application:
```
http://localhost:8000
```

### Docker Configuration

The application runs in a single container with both frontend and backend:

- **Port**: 8000
- **Volumes**:
  - `./downloads:/app/downloads` - Downloaded files
  - `./logs:/app/logs` - Application logs

### Environment Variables

You can configure the application via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | CORS allowed origins |
| `TZ` | `Asia/Hong_Kong` | Container timezone |

### Docker Commands

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Stop and remove volumes (deletes downloads)
docker-compose down -v

# Rebuild after changes
docker-compose up -d --build

# Access container shell
docker-compose exec youtube-downloader sh
```

### Health Check

The container includes a health check that monitors the API:
- **Interval**: 30s
- **Timeout**: 10s
- **Retries**: 3
- **Start period**: 10s

## Local Development

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend/metube
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

### Building Frontend for Production

```bash
cd frontend/metube
npm run build
```

The build output will be in the `dist/` directory, which the backend serves as static files.

## API Endpoints

### Health Check
```
GET /
```
Returns API status and basic information.

### Get Video Info
```
POST /api/get-video-info
```

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=..."
}
```

**Response:**
```json
{
  "title": "Video Title",
  "duration": 120,
  "thumbnail": "https://...",
  "uploader": "Channel Name",
  "formats": [
    {
      "resolution": "1080p",
      "format_id": "137",
      "ext": "mp4",
      "filesize": 12345678
    }
  ]
}
```

### Start Download
```
POST /api/download/start
```

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "format": "1080p",
  "output_format": "mp4"
}
```

**Parameters:**
- `format`: Video quality (best, 4K, 2160p, 1440p, 1080p, 720p, 480p, 360p, 240p, 144p, audio)
- `output_format`: File format (mp4, webm, original)

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Download queued"
}
```

### Download Progress (SSE)
```
GET /api/download/progress/{job_id}
```

Returns Server-Sent Events stream with real-time progress updates.

**Progress Data:**
```json
{
  "status": "downloading",
  "percentage": 45.5,
  "downloaded": 12345678,
  "total": 27182818,
  "speed": 1048576,
  "eta": 15,
  "filename": "/path/to/file"
}
```

### Get Download Status
```
GET /api/download/status/{job_id}
```

Returns current status of a download job.

### Download File
```
GET /api/download/file/{job_id}
```

Downloads the completed file. Auto-deletes after 5 minutes.

### Cancel Download
```
DELETE /api/download/{job_id}
```

Cancels download and cleans up files.

## Project Structure

```
youtube-downloader/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── downloads/          # Downloaded files directory
│   └── youtube_downloader.log  # Application logs
├── frontend/
│   └── metube/
│       ├── src/
│       │   ├── components/  # React components
│       │   ├── App.tsx      # Main application
│       │   └── main.tsx     # Entry point
│       ├── package.json     # Node dependencies
│       ├── vite.config.ts   # Vite configuration
│       └── dist/           # Production build output
├── Dockerfile              # Multi-stage build configuration
├── docker-compose.yml      # Docker orchestration
├── .dockerignore          # Docker ignore patterns
└── README.md              # This file
```

## Download Options

### Video Quality Options
- **Best**: Highest available quality
- **2160p** (4K): 3840x2160
- **1440p** (2K): 2560x1440
- **1080p** (Full HD): 1920x1080
- **720p** (HD): 1280x720
- **480p**: 854x480
- **360p**: 640x360
- **240p**: 426x240
- **144p**: 256x144
- **Audio**: Audio only (MP3)

### Output Format Options
- **MP4**: H.264 video + AAC audio (widest compatibility)
- **WebM**: VP9/VP8 video + Vorbis/Opus audio (smaller file size)
- **Original**: Native format from YouTube

## Limitations

- Maximum file size: 5GB
- Requires at least 5GB free disk space
- Videos may be restricted based on YouTube's policy or region
- Auto-deletion of downloaded files after 5 minutes

## Troubleshooting

### Download Fails
- Check if the video URL is valid and accessible
- Verify the video is not region-restricted
- Check disk space: `docker-compose exec youtube-downloader df -h`

### Container Won't Start
- Check Docker is running: `docker ps`
- View logs: `docker-compose logs`
- Ensure port 8000 is not in use

### Frontend Not Loading
- Clear browser cache
- Check container health: `docker-compose ps`
- Verify the frontend build completed: `docker-compose exec youtube-downloader ls -la /app/frontend/build`

## License

This project is for educational purposes only. Please respect YouTube's Terms of Service and copyright laws.

## Credits

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Video downloads powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Frontend built with [React](https://react.dev/) and [Vite](https://vitejs.dev/)
