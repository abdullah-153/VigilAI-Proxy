# VigilAI-Proxy Automation Test Runner (run_tests.ps1)
# Installs dependencies, runs server in background, executes tests, and clean shuts down.

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Initializing VigilAI Test Automation Harness..." -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Installing dependencies
Write-Host "[1/4] Checking and installing test dependencies..." -ForegroundColor Green
pip install -r requirements-test.txt

# Playwright setup if browser tests are needed
# Write-Host "Setting up Playwright browser binaries..." -ForegroundColor Green
# playwright install chromium

# 2. Starting FastAPI application server
Write-Host "[2/4] Spin up FastAPI gateway in the background..." -ForegroundColor Green
$serverProc = Start-Process python -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -PassThru -NoNewWindow

Write-Host "Waiting 3 seconds for server boot..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 3. Running pytest suite
Write-Host "[3/4] Launching Pytest suites..." -ForegroundColor Green
$testFailed = $false
try {
    # Run only API tests since browser tests require full Playwright browser drivers preloaded
    pytest -v -k "test_api_" tests/
} catch {
    Write-Host "Test execution failed." -ForegroundColor Red
    $testFailed = $true
}

# 4. Cleaning up and shutting down uvicorn
Write-Host "[4/4] Tearing down background servers..." -ForegroundColor Green
if ($serverProc) {
    Stop-Process -Id $serverProc.Id -Force
    Write-Host "Server process ($($serverProc.Id)) terminated successfully." -ForegroundColor Green
}

Write-Host "=============================================" -ForegroundColor Cyan
if ($testFailed) {
    Write-Host "TESTS COMPLETED WITH FAILURES." -ForegroundColor Red
    exit 1
} else {
    Write-Host "ALL TESTS PASSED SUCCESSFULLY." -ForegroundColor Green
    exit 0
}
