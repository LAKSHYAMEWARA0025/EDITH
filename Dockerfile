FROM python:3.10-slim

# Install system dependencies required for OpenCV and gym-pybullet-drones
RUN apt-get update && apt-get install -y git libgl1-mesa-glx libglib2.0-0

# Set the working directory
WORKDIR /app

# Copy the requirements file and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gym-pybullet-drones from github
RUN pip install git+https://github.com/utiasDSL/gym-pybullet-drones.git

# Copy the rest of the application
COPY . /app

# Expose port 8000 for FastAPI
EXPOSE 8000

# Start the server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
