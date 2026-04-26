# EDITH Docker Deployment Guide

## Overview

This guide covers building, running, and deploying the EDITH drone environment using Docker. The environment is packaged as a containerized FastAPI server that can be deployed locally or to Hugging Face Spaces.

## Prerequisites

- **Docker**: Version 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: Version 1.29+ (included with Docker Desktop)
- **Git**: For cloning and version control
- **Python 3.10**: For local development (optional)

## Quick Start

### 1. Build the Docker Image

```bash
cd EDITH
docker build -t edith-mission-commander:latest .
```

**Build time**: ~5-10 minutes (downloads PyBullet, gym-pybullet-drones, dependencies)

### 2. Run the Container

```bash
docker run -d \
  --name edith-env \
  -p 8000:8000 \
  -e EDITH_GUI=false \
  -e EDITH_TASK=task1 \
  edith-mission-commander:latest
```

### 3. Verify It's Running

```bash
# Check health
curl http://localhost:8000/tools

# Expected output:
# {"tools": ["get_drone_status", "move_drone_to", ...]}
```

### 4. Test the Environment

```bash
# Reset environment
curl -X POST http://localhost:8000/reset

# Execute a step
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_mission_status", "args": {}}'
```

## Using Docker Compose (Recommended)

Docker Compose simplifies container management:

```bash
# Start the environment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the environment
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## Environment Variables

Configure the environment using these variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `EDITH_GUI` | `false` | Enable PyBullet GUI (use `true` for visualization) |
| `EDITH_TASK` | `task1` | Task type: `task1`, `task2`, or `task3` |

**Example with GUI enabled** (requires X11 forwarding on Linux):
```bash
docker run -d \
  --name edith-env \
  -p 8000:8000 \
  -e EDITH_GUI=true \
  -e EDITH_TASK=task2 \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  edith-mission-commander:latest
```

## Docker Image Details

### Base Image
- **Python 3.10-slim**: Minimal Debian-based Python image
- **Size**: ~800MB (includes PyBullet, OpenCV, gym-pybullet-drones)

### Installed Dependencies

**System packages:**
- `git`: For installing gym-pybullet-drones from GitHub
- `libgl1-mesa-glx`, `libgl1-mesa-dri`: OpenGL for PyBullet rendering
- `libglib2.0-0`, `libsm6`, `libxext6`, `libxrender-dev`: OpenCV dependencies
- `libgomp1`: OpenMP for parallel processing
- `curl`, `wget`: Health checks and utilities

**Python packages:**
- `pybullet==3.2.6`: Physics simulation (Python 3.10 compatible)
- `gym-pybullet-drones`: Drone simulation framework
- `fastapi`, `uvicorn`: Web server
- `openenv`: OpenEnv framework
- `numpy`, `opencv-python`, `Pillow`: Core dependencies

### File Structure in Container

```
/app/
├── core/               # Scene management, vision, collision detection
├── wrapper/            # Environment wrapper, reward calculator
├── server/             # FastAPI application
├── openenv.yaml        # OpenEnv manifest
├── README.md           # Documentation
└── requirements.txt    # Python dependencies
```

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs edith-env
```

**Common issues:**
- Port 8000 already in use: Change port mapping `-p 8001:8000`
- Insufficient memory: Increase Docker memory limit (Settings → Resources)

### Health Check Failing

```bash
# Check if server is responding
docker exec edith-env curl http://localhost:8000/tools

# Check Python process
docker exec edith-env ps aux | grep uvicorn
```

### PyBullet Import Error

If you see `ImportError: libGL.so.1: cannot open shared object file`:

```bash
# Rebuild with --no-cache to ensure all dependencies install
docker build --no-cache -t edith-mission-commander:latest .
```

### Slow Build Times

**Use BuildKit for faster builds:**
```bash
DOCKER_BUILDKIT=1 docker build -t edith-mission-commander:latest .
```

**Cache layers:**
- Requirements are installed before copying code
- Rebuilds only copy changed files

## Deployment to Hugging Face Spaces

### Prerequisites

1. **Hugging Face account**: [Sign up](https://huggingface.co/join)
2. **HF CLI installed**: `pip install huggingface_hub`
3. **Login**: `huggingface-cli login`

### Deployment Steps

#### Option 1: Using Hugging Face Spaces UI

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Configure:
   - **Name**: `edith-mission-commander`
   - **License**: MIT
   - **SDK**: Docker
   - **Hardware**: CPU Basic (free tier)
4. Clone the Space repository:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/edith-mission-commander
   cd edith-mission-commander
   ```
5. Copy EDITH files:
   ```bash
   cp -r ../EDITH/core .
   cp -r ../EDITH/wrapper .
   cp -r ../EDITH/server .
   cp ../EDITH/Dockerfile .
   cp ../EDITH/requirements.txt .
   cp ../EDITH/openenv.yaml .
   cp ../EDITH/README.md .
   ```
6. Commit and push:
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push
   ```

#### Option 2: Using OpenEnv CLI (if available)

```bash
cd EDITH
openenv push --space YOUR_USERNAME/edith-mission-commander
```

### Space Configuration

Create a `README.md` in the Space with frontmatter:

```yaml
---
title: EDITH Mission Commander
emoji: 🚁
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# EDITH: Emergency Drone Intelligence & Tactical Handler

[Your environment description here]
```

### Verify Deployment

Once deployed, your Space will be available at:
```
https://huggingface.co/spaces/YOUR_USERNAME/edith-mission-commander
```

Test the API:
```bash
curl https://YOUR_USERNAME-edith-mission-commander.hf.space/tools
```

## Performance Optimization

### Reduce Image Size

**Multi-stage build** (advanced):
```dockerfile
FROM python:3.10-slim AS builder
# Install dependencies
...

FROM python:3.10-slim
# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
...
```

### Faster Startup

**Pre-compile Python files:**
```dockerfile
RUN python -m compileall /app
```

### Memory Limits

**Set container memory limit:**
```bash
docker run -d \
  --name edith-env \
  --memory="2g" \
  --memory-swap="2g" \
  -p 8000:8000 \
  edith-mission-commander:latest
```

## Development Workflow

### Local Development with Hot Reload

```bash
# Mount local code for development
docker run -d \
  --name edith-dev \
  -p 8000:8000 \
  -v $(pwd)/core:/app/core \
  -v $(pwd)/wrapper:/app/wrapper \
  -v $(pwd)/server:/app/server \
  edith-mission-commander:latest \
  uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

### Testing Changes

```bash
# Rebuild after code changes
docker-compose up -d --build

# Run tests inside container
docker exec edith-env python -m pytest tests/
```

## Security Considerations

### Production Deployment

1. **Don't expose internal ports**: Use reverse proxy (nginx, Caddy)
2. **Add authentication**: Implement API keys or OAuth
3. **Rate limiting**: Prevent abuse
4. **HTTPS**: Use TLS certificates (Let's Encrypt)

### Environment Secrets

**Never commit secrets to Git!**

Use Docker secrets or environment files:
```bash
docker run -d \
  --name edith-env \
  --env-file .env.production \
  -p 8000:8000 \
  edith-mission-commander:latest
```

## Monitoring

### Container Stats

```bash
# Real-time stats
docker stats edith-env

# Logs
docker logs -f edith-env --tail 100
```

### Health Monitoring

The container includes a health check that runs every 30 seconds:
```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' edith-env
```

## Cleanup

```bash
# Stop and remove container
docker stop edith-env
docker rm edith-env

# Remove image
docker rmi edith-mission-commander:latest

# Clean up all unused Docker resources
docker system prune -a
```

## Additional Resources

- **OpenEnv Documentation**: [https://openenv.dev](https://openenv.dev)
- **Docker Best Practices**: [https://docs.docker.com/develop/dev-best-practices/](https://docs.docker.com/develop/dev-best-practices/)
- **Hugging Face Spaces**: [https://huggingface.co/docs/hub/spaces](https://huggingface.co/docs/hub/spaces)
- **PyBullet Documentation**: [https://pybullet.org](https://pybullet.org)

## Support

For issues or questions:
- **GitHub Issues**: [Your repository]
- **Hugging Face Discussions**: [Your Space discussions]
- **OpenEnv Discord**: [Community link]
