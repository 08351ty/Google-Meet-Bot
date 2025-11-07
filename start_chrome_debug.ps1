# PowerShell script to start Chrome with remote debugging enabled using your existing profile
# This script will automatically detect your Chrome installation and profile directory

$DEBUG_PORT = 9222

# Try to find Chrome executable
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
    Write-Host "ERROR: Chrome executable not found!" -ForegroundColor Red
    Write-Host "Please set CHROME_PATH environment variable or install Chrome."
    Read-Host "Press Enter to exit"
    exit 1
}

# Get user profile directory
$userDataDir = Join-Path $env:USERPROFILE "AppData\Local\Google\Chrome\User Data"

Write-Host "Starting Chrome with remote debugging on port $DEBUG_PORT..." -ForegroundColor Green
Write-Host "Using profile: $userDataDir" -ForegroundColor Cyan
Write-Host ""

# Kill any existing Chrome processes first
Write-Host "Closing any existing Chrome instances..." -ForegroundColor Yellow
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start Chrome with remote debugging
# Note: We need to pass arguments as a single string to properly handle paths with spaces
$arguments = "--remote-debugging-port=$DEBUG_PORT --user-data-dir=`"$userDataDir`""
Write-Host "Command: `"$chromePath`" $arguments" -ForegroundColor Gray
Write-Host ""

try {
    Start-Process -FilePath $chromePath -ArgumentList $arguments -ErrorAction Stop
    Write-Host "Chrome started! Waiting 3 seconds for it to initialize..." -ForegroundColor Green
    Start-Sleep -Seconds 3
    
    # Verify the port is listening
    $portCheck = Test-NetConnection -ComputerName localhost -Port $DEBUG_PORT -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($portCheck) {
        Write-Host "[OK] Chrome is now listening on port $DEBUG_PORT" -ForegroundColor Green
        Write-Host "You can now run your Python script!" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Chrome started but port $DEBUG_PORT is not yet listening." -ForegroundColor Yellow
        Write-Host "Please wait a few seconds and try again, or check for errors." -ForegroundColor Yellow
    }
} catch {
    Write-Host "ERROR: Failed to start Chrome" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

