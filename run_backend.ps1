<#
.SYNOPSIS
    Automated, robust PowerShell runner for Raise India FastAPI Backend.
.DESCRIPTION
    Sets PYTHONPATH, frees stale port bindings, and launches Uvicorn with an explicit
    reload directory to prevent Windows WatchFiles path spacing loops.
#>

[CmdletBinding()]
param (
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

# 1. Determine Project Root Directory
$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { "E:\raise india" }
Set-Location -LiteralPath $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [Raise India] Starting FastAPI Backend Service" -ForegroundColor Green
Write-Host " Root Directory   : $ProjectRoot" -ForegroundColor DarkGray
Write-Host " Host / Port      : http://${HostAddress}:${Port}" -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Cyan

# 2. Check and Free Port 8000 if occupied (including process tree)
$ActiveConn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($ActiveConn) {
    Write-Host "[!] Port $Port is currently in use. Terminating stale process tree..." -ForegroundColor Yellow
    foreach ($conn in $ActiveConn) {
        $stalePid = $conn.OwningProcess
        if ($stalePid -gt 4) {
            Write-Host "    Terminating PID $stalePid (and child processes) on port $Port..." -ForegroundColor DarkYellow
            & taskkill.exe /F /T /PID $stalePid 2>$null | Out-Null
        }
    }
    Start-Sleep -Seconds 1
}

# 3. Locate Python Virtual Environment and Uvicorn
$VenvPython = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"
$VenvUvicorn = Join-Path $ProjectRoot "backend\venv\Scripts\uvicorn.exe"
$ReloadDirectory = Join-Path $ProjectRoot "backend\app"

if (-not (Test-Path -LiteralPath $VenvUvicorn)) {
    Write-Host "[!] Virtualenv uvicorn not found at $VenvUvicorn. Falling back to system uvicorn..." -ForegroundColor Yellow
    $UvicornCmd = "uvicorn"
} else {
    $UvicornCmd = $VenvUvicorn
}

# 4. Set Environment Variables
$env:PYTHONPATH = $ProjectRoot
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUNBUFFERED = "1"

Write-Host "[+] PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green
Write-Host "[+] Explicit reload directory: $ReloadDirectory" -ForegroundColor Green
Write-Host "[+] Launching Uvicorn server..." -ForegroundColor Cyan

# 5. Execute Uvicorn with explicit reload directory
& $UvicornCmd backend.app.main:app --host $HostAddress --port $Port --reload --reload-dir $ReloadDirectory
