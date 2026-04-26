FROM python:3.10-slim

# Install system dependencies for PyBullet, OpenCV, and OpenGL
# Note: OpenGL libraries needed even in headless mode for offscreen rendering
RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install PyBullet (Python 3.10 compatible)
RUN pip install --no-cache-dir pybullet==3.2.6

# Install gym-pybullet-drones from GitHub
RUN pip install --no-cache-dir git+https://github.com/utiasDSL/gym-pybullet-drones.git

# Copy application code
COPY core/ /app/core/
COPY wrapper/ /app/wrapper/
COPY server/ /app/server/
COPY openenv.yaml /app/
COPY README.md /app/

# Set environment variables for headless operation
ENV PYTHONUNBUFFERED=1
ENV EDITH_GUI=false
ENV EDITH_TASK=task1
# PyBullet headless mode (no display required)
ENV DISPLAY=
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV MESA_GLSL_VERSION_OVERRIDE=330

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/tools || exit 1

# Run FastAPI server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
