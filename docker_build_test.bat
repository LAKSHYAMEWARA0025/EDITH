@echo off
REM EDITH Docker Build and Test Script (Windows)
REM Usage: docker_build_test.bat

setlocal enabledelayedexpansion

echo ==========================================
echo EDITH Docker Build and Test
echo ==========================================
echo.

REM Configuration
set IMAGE_NAME=edith-mission-commander
set CONTAINER_NAME=edith-test
set PORT=7860

REM Step 1: Clean up existing containers
echo [1/6] Cleaning up existing containers...
docker stop %CONTAINER_NAME% 2>nul
docker rm %CONTAINER_NAME% 2>nul
echo [OK] Cleanup complete
echo.

REM Step 2: Build Docker image
echo [2/6] Building Docker image...
echo This may take 5-10 minutes on first build...
docker build -t %IMAGE_NAME%:latest .
if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)
echo [OK] Build complete
echo.

REM Step 3: Start container
echo [3/6] Starting container...
docker run -d --name %CONTAINER_NAME% -p %PORT%:7860 -e EDITH_GUI=false -e EDITH_TASK=task1 %IMAGE_NAME%:latest
if errorlevel 1 (
    echo [ERROR] Failed to start container
    exit /b 1
)
echo [OK] Container started
echo.

REM Step 4: Wait for container to be healthy
echo [4/6] Waiting for container to be healthy...
echo This may take 30-40 seconds...

set MAX_WAIT=60
set ELAPSED=0

:wait_loop
if %ELAPSED% geq %MAX_WAIT% (
    echo [ERROR] Container failed to become healthy
    echo Showing container logs:
    docker logs %CONTAINER_NAME%
    exit /b 1
)

docker exec %CONTAINER_NAME% curl -f http://localhost:7860/tools >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    set /a ELAPSED+=2
    echo|set /p=.
    goto wait_loop
)

echo.
echo [OK] Container is healthy
echo.

REM Step 5: Run API tests
echo [5/6] Running API tests...

REM Test 1: Get tools
echo   Testing /tools endpoint...
curl -s http://localhost:%PORT%/tools > temp_response.txt
findstr /C:"get_drone_status" temp_response.txt >nul
if errorlevel 1 (
    echo [ERROR] /tools test failed
    type temp_response.txt
    del temp_response.txt
    exit /b 1
)
echo   [OK] /tools test passed
del temp_response.txt

REM Test 2: Reset environment (with session)
echo   Testing /reset endpoint...
curl -s -X POST http://localhost:%PORT%/reset > temp_response.txt
findstr /C:"session_id" temp_response.txt >nul
if errorlevel 1 (
    echo [ERROR] /reset test failed - no session_id returned
    type temp_response.txt
    del temp_response.txt
    exit /b 1
)
echo   [OK] /reset test passed
del temp_response.txt

REM Test 3: Execute step with session
echo   Testing /step endpoint with session...
curl -s -X POST http://localhost:%PORT%/step -H "Content-Type: application/json" -H "x-session-id: test-session-123" -d "{\"tool\": \"get_mission_status\", \"args\": {}}" > temp_response.txt
findstr /C:"reward" temp_response.txt >nul
if errorlevel 1 (
    echo [ERROR] /step test failed
    type temp_response.txt
    del temp_response.txt
    exit /b 1
)
echo   [OK] /step test passed
del temp_response.txt

echo [OK] All API tests passed
echo.

REM Step 6: Summary
echo [6/6] Summary
echo ==========================================
echo Image:     %IMAGE_NAME%:latest
echo Container: %CONTAINER_NAME%
echo Port:      http://localhost:%PORT%
echo Status:    Running and healthy
echo ==========================================
echo.

echo Container is ready for use!
echo.
echo Useful commands:
echo   View logs:        docker logs -f %CONTAINER_NAME%
echo   Stop container:   docker stop %CONTAINER_NAME%
echo   Remove container: docker rm %CONTAINER_NAME%
echo   Shell access:     docker exec -it %CONTAINER_NAME% /bin/bash
echo.
echo API endpoints:
echo   GET  http://localhost:%PORT%/tools
echo   POST http://localhost:%PORT%/reset
echo   POST http://localhost:%PORT%/step
echo.

endlocal
