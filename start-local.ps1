# Khoi dong stack local (KHONG Docker): Postgres tren may + venv backend + Next dev.
# Chay tu thu muc goc repo:
#   .\start-local.ps1
# Truoc do: copy backend\.env.example -> backend\.env va chinh mat khau Postgres neu can.
param(
    [switch]$KeepPorts
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$VenvPy = Join-Path $Backend ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Backend ".venv\Scripts\pip.exe"
$VenvAlembic = Join-Path $Backend ".venv\Scripts\alembic.exe"
$VenvUvicorn = Join-Path $Backend ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Write-Error "Thieu backend\.env — copy tu backend\.env.example, dat DATABASE_URL dung Postgres local (vd: postgres:postgres@127.0.0.1:5432)."
    exit 1
}

if (-not $KeepPorts) {
    & (Join-Path $Root "stop-local.ps1")
    Start-Sleep -Seconds 1
}

$python = $null
foreach ($c in @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    )) {
    if (Test-Path $c) { $python = $c; break }
}
if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $python -or -not (Test-Path $python)) {
    Write-Error "Khong tim thay Python 3.12+. Cai tu winget: winget install Python.Python.3.12"
    exit 1
}

if (-not (Test-Path $VenvPy)) {
    Write-Host "Tao venv backend..."
    Push-Location $Backend
    try {
        & $python -m venv .venv
    }
    finally {
        Pop-Location
    }
}

Write-Host "pip install (co the vai giay)..."
& $VenvPip install -q -r (Join-Path $Backend "requirements.txt")

Write-Host "alembic upgrade head..."
Push-Location $Backend
try {
    & $VenvAlembic upgrade head
}
finally {
    Pop-Location
}

Write-Host "Mo 2 cua so: backend :8000 va frontend :3000"
Start-Process powershell.exe -WorkingDirectory $Backend -ArgumentList @(
    "-NoExit", "-Command", ".\.venv\Scripts\uvicorn.exe main:app --reload --host 0.0.0.0 --port 8000"
)
Start-Sleep -Seconds 2
Start-Process powershell.exe -WorkingDirectory $Frontend -ArgumentList @(
    "-NoExit", "-Command", "npm run dev"
)

Write-Host ""
Write-Host "OK. Test:"
Write-Host "  API   http://localhost:8000/docs"
Write-Host "  UI    http://localhost:3000"
Write-Host "  Health http://localhost:8000/api/v1/health"
