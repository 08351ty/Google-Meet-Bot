# Robust PowerShell script to start Chrome with remote debugging
# This script ensures all Chrome processes are closed and lock files are cleared

$DEBUG_PORT = 9222

# Function to kill all Chrome processes
function Stop-AllChrome {
    Write-Host "Step 1: Stopping all Chrome processes..." -ForegroundColor Yellow
    $chromeProcesses = Get-Process chrome -ErrorAction SilentlyContinue
    if ($chromeProcesses) {
        Write-Host "  Found $($chromeProcesses.Count) Chrome process(es)" -ForegroundColor Gray
        $chromeProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  All Chrome processes stopped." -ForegroundColor Green
    } else {
        Write-Host "  No Chrome processes found." -ForegroundColor Green
    }
    
    # Wait for processes to fully terminate
    Write-Host "  Waiting for processes to terminate..." -ForegroundColor Gray
    $maxWait = 10
    $waited = 0
    while ($waited -lt $maxWait) {
        $stillRunning = Get-Process chrome -ErrorAction SilentlyContinue
        if (-not $stillRunning) {
            break
        }
        Start-Sleep -Seconds 1
        $waited++
        Write-Host "    Still waiting... ($waited/$maxWait)" -ForegroundColor Gray
    }
    
    if (Get-Process chrome -ErrorAction SilentlyContinue) {
        Write-Host "  [WARNING] Some Chrome processes may still be running" -ForegroundColor Yellow
    } else {
        Write-Host "  All Chrome processes terminated." -ForegroundColor Green
    }
}

# Function to clear Chrome lock files
function Clear-ChromeLocks {
    Write-Host "`nStep 2: Clearing Chrome lock files..." -ForegroundColor Yellow
    $userDataDir = Join-Path $env:USERPROFILE "AppData\Local\Google\Chrome\User Data"
    $lockFile = Join-Path $userDataDir "SingletonLock"
    $lockCookie = Join-Path $userDataDir "SingletonCookie"
    
    if (Test-Path $lockFile) {
        try {
            Remove-Item $lockFile -Force -ErrorAction Stop
            Write-Host "  Removed SingletonLock" -ForegroundColor Green
        } catch {
            Write-Host "  [WARNING] Could not remove SingletonLock: $_" -ForegroundColor Yellow
        }
    }
    
    if (Test-Path $lockCookie) {
        try {
            Remove-Item $lockCookie -Force -ErrorAction Stop
            Write-Host "  Removed SingletonCookie" -ForegroundColor Green
        } catch {
            Write-Host "  [WARNING] Could not remove SingletonCookie: $_" -ForegroundColor Yellow
        }
    }
    
    Write-Host "  Lock files cleared." -ForegroundColor Green
}

# Find Chrome executable
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "Chrome Remote Debugging Startup Script" -ForegroundColor Cyan  
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

$chromePath = $null
$possiblePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $chromePath = $path
        break
    }
}

if (-not $chromePath) {
    Write-Host "[ERROR] Chrome executable not found!" -ForegroundColor Red
    Write-Host "Please install Chrome or set CHROME_PATH environment variable." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Chrome found: $chromePath" -ForegroundColor Green

# Get user data directory
$userDataDir = Join-Path $env:USERPROFILE "AppData\Local\Google\Chrome\User Data"
Write-Host "Profile directory: $userDataDir" -ForegroundColor Cyan
Write-Host ""

# Stop all Chrome processes
Stop-AllChrome

# Clear lock files
Clear-ChromeLocks

# Wait a bit more for everything to settle
Write-Host "`nStep 3: Waiting for system to settle..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Start Chrome with debugging
Write-Host "`nStep 4: Starting Chrome with remote debugging..." -ForegroundColor Yellow
$arguments = "--remote-debugging-port=$DEBUG_PORT --user-data-dir=`"$userDataDir`""

Write-Host "  Command: `"$chromePath`" $arguments" -ForegroundColor Gray
Write-Host ""

try {
    $process = Start-Process -FilePath $chromePath -ArgumentList $arguments -PassThru -ErrorAction Stop
    Write-Host "  Chrome process started (PID: $($process.Id))" -ForegroundColor Green
    
    # Wait for Chrome to initialize
    Write-Host "`nStep 5: Waiting for Chrome to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Verify the port is listening
    Write-Host "`nStep 6: Verifying remote debugging port..." -ForegroundColor Yellow
    $portCheck = Test-NetConnection -ComputerName localhost -Port $DEBUG_PORT -InformationLevel Quiet -WarningAction SilentlyContinue
    
    if ($portCheck) {
        Write-Host ""
        Write-Host ("=" * 60) -ForegroundColor Green
        Write-Host "[SUCCESS] Chrome is running with remote debugging!" -ForegroundColor Green
        Write-Host "  Port $DEBUG_PORT is listening" -ForegroundColor Green
        Write-Host "  You can now run your Python script" -ForegroundColor Green
        Write-Host ("=" * 60) -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[WARNING] Chrome started but port $DEBUG_PORT is not listening yet." -ForegroundColor Yellow
        Write-Host "This might mean:" -ForegroundColor Yellow
        Write-Host "  1. Chrome needs more time to start (wait 10-15 seconds)" -ForegroundColor Yellow
        Write-Host "  2. There was an error starting Chrome" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Try running: python test_chrome_connection.py" -ForegroundColor Cyan
    }
    
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to start Chrome" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Please try:" -ForegroundColor Yellow
    Write-Host "  1. Manually close all Chrome windows" -ForegroundColor Yellow
    Write-Host "  2. Check Task Manager for any chrome.exe processes" -ForegroundColor Yellow
    Write-Host "  3. Run this script again" -ForegroundColor Yellow
    Read-Host "`nPress Enter to exit"
    exit 1
}

Write-Host ""

