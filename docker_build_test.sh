#!/bin/bash
# EDITH Docker Build and Test Script
# Usage: ./docker_build_test.sh

set -e  # Exit on error

echo "=========================================="
echo "EDITH Docker Build and Test"
echo "=========================================="
echo ""

# Configuration
IMAGE_NAME="edith-mission-commander"
CONTAINER_NAME="edith-test"
PORT=8000

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Clean up existing containers
echo -e "${YELLOW}[1/6] Cleaning up existing containers...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# Step 2: Build Docker image
echo -e "${YELLOW}[2/6] Building Docker image...${NC}"
echo "This may take 5-10 minutes on first build..."
DOCKER_BUILDKIT=1 docker build -t $IMAGE_NAME:latest .
echo -e "${GREEN}✓ Build complete${NC}"
echo ""

# Step 3: Start container
echo -e "${YELLOW}[3/6] Starting container...${NC}"
docker run -d \
  --name $CONTAINER_NAME \
  -p $PORT:8000 \
  -e EDITH_GUI=false \
  -e EDITH_TASK=task1 \
  $IMAGE_NAME:latest

echo -e "${GREEN}✓ Container started${NC}"
echo ""

# Step 4: Wait for container to be healthy
echo -e "${YELLOW}[4/6] Waiting for container to be healthy...${NC}"
echo "This may take 30-40 seconds..."

MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker exec $CONTAINER_NAME curl -f http://localhost:8000/tools > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Container is healthy${NC}"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${RED}✗ Container failed to become healthy${NC}"
    echo "Showing container logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi
echo ""

# Step 5: Run API tests
echo -e "${YELLOW}[5/6] Running API tests...${NC}"

# Test 1: Get tools
echo -n "  Testing /tools endpoint... "
TOOLS_RESPONSE=$(curl -s http://localhost:$PORT/tools)
if echo "$TOOLS_RESPONSE" | grep -q "get_drone_status"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Response: $TOOLS_RESPONSE"
    exit 1
fi

# Test 2: Reset environment
echo -n "  Testing /reset endpoint... "
RESET_RESPONSE=$(curl -s -X POST http://localhost:$PORT/reset)
if echo "$RESET_RESPONSE" | grep -q "state"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Response: $RESET_RESPONSE"
    exit 1
fi

# Test 3: Execute step
echo -n "  Testing /step endpoint... "
STEP_RESPONSE=$(curl -s -X POST http://localhost:$PORT/step \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_mission_status", "args": {}}')
if echo "$STEP_RESPONSE" | grep -q "reward"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Response: $STEP_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ All API tests passed${NC}"
echo ""

# Step 6: Summary
echo -e "${YELLOW}[6/6] Summary${NC}"
echo "=========================================="
echo -e "Image:     ${GREEN}$IMAGE_NAME:latest${NC}"
echo -e "Container: ${GREEN}$CONTAINER_NAME${NC}"
echo -e "Port:      ${GREEN}http://localhost:$PORT${NC}"
echo -e "Status:    ${GREEN}Running and healthy${NC}"
echo "=========================================="
echo ""

echo "Container is ready for use!"
echo ""
echo "Useful commands:"
echo "  View logs:        docker logs -f $CONTAINER_NAME"
echo "  Stop container:   docker stop $CONTAINER_NAME"
echo "  Remove container: docker rm $CONTAINER_NAME"
echo "  Shell access:     docker exec -it $CONTAINER_NAME /bin/bash"
echo ""
echo "API endpoints:"
echo "  GET  http://localhost:$PORT/tools"
echo "  POST http://localhost:$PORT/reset"
echo "  POST http://localhost:$PORT/step"
echo ""
