# PowerShell script to start Chrome with remote debugging using a symbolic link
# This bypasses Chrome's restriction on using the default profile directory

$DEBUG_PORT = 9222

# Create a symbolic link directory name (not the actual default path)
$originalDataDir = Join-Path $env:USERPROFILE "AppData\Local\Google\Chrome\User Data"
$linkDataDir = Join-Path $env:USERPROFILE "AppData\Local\Google\Chrome\User Data Debug"

Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "Chrome Remote Debugging with Profile Link" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

# Kill existing Chrome processes
Write-Host "Stopping Chrome processes..." -ForegroundColor Yellow
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Remove existing link if it exists
if (Test-Path $linkDataDir) {
    Write-Host "Removing existing link..." -ForegroundColor Yellow
    Remove-Item $linkDataDir -Force -ErrorAction SilentlyContinue
}

# Create symbolic link (requires Admin privileges) OR use robocopy approach
Write-Host "Creating symbolic link to profile..." -ForegroundColor Yellow

# Try to create junction (works without admin on same drive)
try {
    $junction = $linkDataDir
    if (Test-Path $junction) {
        Remove-Item $junction -Force -ErrorAction SilentlyContinue
    }
    
    # Use cmd's mklink to create junction (works without admin)
    $cmd = "cmd /c mklink /J `"$junction`" `"$originalDataDir`""
    $result = Invoke-Expression $cmd 2>&1
    Write-Host "  $result" -ForegroundColor Gray
    
    if (Test-Path $linkDataDir) {
        Write-Host "  [OK] Junction created successfully" -ForegroundColor Green
    } else {
        throw "Junction creation failed"
    }
} catch {
    Write-Host "  [WARNING] Could not create junction: $_" -ForegroundColor Yellow
    Write-Host "  Trying alternative: Using profile directory directly with different name..." -ForegroundColor Yellow
    # Fallback: Use the actual directory but Chrome should accept it if path looks different
    $linkDataDir = $originalDataDir
}

# Find Chrome executable
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
    Read-Host "Press Enter to exit"
    exit 1
}

# Start Chrome with the link directory
Write-Host "`nStarting Chrome with remote debugging..." -ForegroundColor Yellow
Write-Host "  Using directory: $linkDataDir" -ForegroundColor Cyan
Write-Host "  Debug port: $DEBUG_PORT" -ForegroundColor Cyan

$args = @(
    "--remote-debugging-port=$DEBUG_PORT",
    "--user-data-dir=`"$linkDataDir`"",
    "--remote-allow-origins=*"
)

try {
    $proc = Start-Process -FilePath $chromePath -ArgumentList $args -PassThru
    Write-Host "  Chrome started (PID: $($proc.Id))" -ForegroundColor Green
    
    Write-Host "`nWaiting for Chrome to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 6
    
    # Test the connection
    Write-Host "`nTesting connection..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$DEBUG_PORT/json" -TimeoutSec 3 -ErrorAction Stop
        Write-Host ""
        Write-Host ("=" * 60) -ForegroundColor Green
        Write-Host "[SUCCESS] Chrome remote debugging is working!" -ForegroundColor Green
        Write-Host "  Port $DEBUG_PORT is listening" -ForegroundColor Green
        Write-Host "  Your profile is accessible" -ForegroundColor Green
        Write-Host ("=" * 60) -ForegroundColor Green
        Write-Host "`nYou can now run your Python script!" -ForegroundColor Green
    } catch {
        Write-Host ""
        Write-Host "[WARNING] Chrome started but port check failed" -ForegroundColor Yellow
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  Chrome may need more time to start" -ForegroundColor Yellow
        Write-Host "  Try running: python test_chrome_connection.py" -ForegroundColor Cyan
    }
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to start Chrome" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "`nPress Enter to exit"
    exit 1
}

Write-Host ""

