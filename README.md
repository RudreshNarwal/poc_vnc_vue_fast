# Browser Automation Studio

A comprehensive browser automation platform with real-time visual feedback through VNC integration. Create, manage, and execute browser automation tasks with an intuitive web interface.

## Features

- **Visual Automation**: Watch your automation tasks execute in real-time through integrated VNC viewer
- **Task Builder**: Create complex automation workflows with step-by-step builder
- **File Integration**: Upload Excel, CSV, and other files for automation prerequisites
- **Real-time Control**: Pause, resume, and interact with running automations
- **WebSocket Communication**: Live status updates and progress tracking
- **Timezone Support**: Consistent timezone handling across all services
- **Passwordless VNC**: Auto-connecting VNC viewer with no password required

## Architecture

- **Backend**: FastAPI with SQLAlchemy, Playwright automation engine
- **Frontend**: Vue.js 3 with Tailwind CSS and noVNC integration
- **VNC Container**: Official Playwright image with Fluxbox desktop and noVNC
- **Database**: PostgreSQL for task and execution storage
- **Cache**: Redis for session management

### VNC + Playwright Integration

The system uses an optimized VNC setup:

- **Base Image**: `mcr.microsoft.com/playwright:v1.40.0-jammy` (official Playwright image)
- **Desktop**: Fluxbox (lightweight, faster than XFCE)
- **Display Server**: Xvfb virtual framebuffer on `:1`
- **VNC Server**: x11vnc for screen capture
- **Web Interface**: noVNC + websockify for browser access
- **Browser**: Chromium launched with `headless=False` and `--display=:1`

### Port Configuration

- **5901**: VNC protocol port
- **6080**: WebSockify port (VNC-to-WebSocket bridge)
- **7900**: noVNC HTTP interface
- **8000**: Backend API
- **3000**: Frontend application

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 4GB RAM available for containers
- Ports 3000, 5901, 7900, 8000 available

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd auto-flow
   ```

2. **Start all services with healthchecks**
   ```bash
   docker-compose up -d
   ```

3. **Monitor service startup** (services start in dependency order)
   ```bash
   docker-compose logs -f vnc      # Check VNC is running
   docker-compose logs -f backend  # Check backend
   docker-compose ps               # Check all service health
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs
   - Direct VNC: http://localhost:7900/vnc.html (no password)
   - Health Status: http://localhost:8000/api/health

5. **Test Playwright + VNC integration**
   ```bash
   # Copy test script to VNC container
   docker cp test_playwright_vnc.py auto-flow-vnc-1:/tmp/
   
   # Run test inside VNC container
   docker exec -it auto-flow-vnc-1 python3 /tmp/test_playwright_vnc.py
   
   # You should see the browser open in the VNC viewer!
   ```

### Production Deployment

For production deployment, set the `VNC_PUBLIC_HOST` environment variable:

```bash
export VNC_PUBLIC_HOST=your-domain.com
docker-compose up -d
```

### Usage

1. **Create a Task**
   - Navigate to "Builder" in the web interface
   - Add automation steps (navigate, click, type, etc.)
   - Save the task

2. **Run Automation**
   - Go to "Tasks" and click "Run" on your task
   - Watch the automation execute in the VNC viewer
   - Use pause/resume controls as needed

3. **Interactive Mode**
   - Add "Interactive Pause" steps to your automation
   - When reached, you can manually interact with the browser
   - Click "Resume" to continue automation

## Automation Actions

### Navigation
- **Navigate**: Go to a URL
- **Click**: Click on an element (CSS selector)
- **Type**: Enter text into an input field
- **Select**: Choose an option from a dropdown
- **Wait**: Wait for element or delay
- **Screenshot**: Capture current page
- **Interactive Pause**: Pause for manual interaction

### File Prerequisites
- Upload Excel/CSV files before automation
- Files are accessible during task execution
- Supports data-driven automation workflows

## Development

### Project Structure

```
auto-flow/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── models/    # Database models
│   │   └── services/  # Business logic
│   └── requirements.txt
├── frontend/          # Vue.js frontend
│   ├── src/
│   │   └── components/
│   └── package.json
├── vnc/              # VNC container
│   ├── Dockerfile
│   └── supervisord.conf
└── docker-compose.yml
```

### Environment Variables

Key environment variables in `backend/.env`:

```env
# Database
DATABASE_URL=postgresql://admin:password@postgres:5432/automation

# VNC Settings
VNC_HOST=vnc
VNC_DISPLAY=:1
VNC_PORT=5901
VNC_WEB_PORT=7900

# Timezone
TIMEZONE=America/New_York

# Playwright
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_TIMEOUT=30000
```

### API Endpoints

- `GET /api/health` - System health check
- `GET /api/vnc/config` - VNC configuration
- `POST /api/tasks/` - Create task
- `GET /api/tasks/` - List tasks
- `POST /api/automation/execute/{task_id}` - Start automation
- `POST /api/automation/pause/{session_id}` - Pause automation
- `POST /api/files/upload` - Upload files

### WebSocket Events

Real-time automation updates via WebSocket:

```javascript
// Connect to session
const ws = new WebSocket(`/ws/${sessionId}`)

// Status updates
{
  "type": "status",
  "status": "running",
  "message": "Executing step 1",
  "data": {
    "current_step": 1,
    "total_steps": 5,
    "screenshot": "/screenshots/step_1.png"
  }
}
```

## Troubleshooting

### VNC Connection Issues
- Check if VNC container is running: `docker-compose logs vnc`
- Verify port 7900 is accessible
- Try direct VNC access: http://localhost:7900/vnc.html
- Check VNC health: `docker-compose ps` (should show "healthy")

### Automation Failures
- Check browser logs in VNC desktop
- Verify CSS selectors are correct
- Ensure target website is accessible
- Check timezone settings for date/time sensitive sites

### Performance Issues
- Increase Docker memory allocation (4GB+ recommended)
- Check available disk space for screenshots
- Monitor container resource usage
- Use `docker-compose ps` to check service health

### Database Issues
- Reset database: `docker-compose down -v && docker-compose up -d`
- Check PostgreSQL logs: `docker-compose logs postgres`
- Verify health: PostgreSQL healthcheck monitors connection

### Network Issues
- For production deployment, ensure `VNC_PUBLIC_HOST` is set correctly
- Check that all ports (3000, 5901, 7900, 8000) are accessible
- Verify WebSocket connections work through firewalls

## Recent Fixes (v1.1)

This implementation includes critical fixes identified in code review:

### ✅ Fixed VNC Server Conflicts
- **Removed redundant startup.sh** that conflicted with supervisord
- **Simplified supervisord configuration** with correct service priorities
- **Eliminated race conditions** between VNC startup methods

### ✅ Fixed Hardcoded Localhost Issue
- **Dynamic hostname detection** in backend VNC config endpoint
- **Production-ready** with `VNC_PUBLIC_HOST` environment variable
- **Docker-aware** hostname resolution for internal communication

### ✅ Added Health Checks
- **Database health monitoring** with pg_isready
- **Redis health checks** with ping command  
- **VNC service monitoring** with netcat port checks
- **Backend health endpoint** with curl verification
- **Dependency ordering** ensures services start in correct sequence

### ✅ Improved WebSocket Management
- **Centralized WebSocket store** prevents connection leaks
- **Connection state tracking** with proper cleanup
- **Error handling** and automatic reconnection logic
- **Memory leak prevention** with proper disconnection

### 🔒 Security Considerations
- **Development mode**: Passwordless VNC for ease of use
- **Production ready**: VNC password support via environment variables
- **Configurable authentication** with `VNC_REQUIRE_AUTH` setting

## Configuration

### Timezone Settings
The system uses America/New_York timezone by default. To change:

1. Update `TZ` environment variable in docker-compose.yml
2. Update `TIMEZONE` in backend/.env
3. Restart containers

### VNC Settings
- Resolution: 1920x1080 (configurable in VNC_RESOLUTION)
- No password required (VNC_NO_PASSWORD=1)
- Shared desktop mode enabled

### Browser Settings
- Chromium with Playwright
- Timezone-aware browser context
- Screenshots after each step
- Headless mode disabled for VNC viewing

## Security Notes

- VNC has no password for development convenience
- Database uses default credentials
- Not configured for production deployment
- All services run in development mode

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker Compose
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Docker Compose logs
3. Open an issue on GitHub
