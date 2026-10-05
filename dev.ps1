# dev.ps1 — Arranque local de IA real + backend (sin frontend)
#
# Uso (desde backend/):
#     npm run dev
#
# Qué hace:
#   1. Valida que exista el venv de ia-service, backend/package.json y app/main.py.
#   2. Si el puerto 8000 ya responde /vision/health, reutiliza ese ia-service.
#      Si lo ocupa OTRO proceso, avisa y NO mata nada.
#   3. Avisa (sin mostrar valores) si falta VISION_IA_URL / VISION_IA_KEY
#      en backend/.env. No define ninguna variable: la config sale de los .env.
#   4. Abre una ventana PowerShell nueva con ia-service (FastAPI + YOLO11n).
#   5. En la terminal actual ejecuta el backend Node (npm run dev:backend).
#
# NO inicia el frontend. NO fija VISION_*. NO mata procesos automaticamente.
# No hay proveedor simulado: sin VISION_IA_URL el backend responde 503.

$ErrorActionPreference = 'Stop'

$raiz        = $PSScriptRoot
$iaDir       = Join-Path $raiz 'ia-service'
$backendDir  = Join-Path $raiz 'backend'
$pythonIa    = Join-Path $iaDir '.venv\Scripts\python.exe'
$iaMain      = Join-Path $iaDir 'app\main.py'
$backendPkg  = Join-Path $backendDir 'package.json'
$iaUrl       = 'http://127.0.0.1:8000'

function Write-Paso([string]$m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Aviso([string]$m) { Write-Host "AVISO: $m" -ForegroundColor Yellow }
function Write-Fallo([string]$m) { Write-Host "ERROR: $m" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# 1. Verificaciones previas
# ---------------------------------------------------------------------------
if (-not (Test-Path -LiteralPath $backendPkg)) {
    Write-Fallo "No se encontro backend\package.json en '$backendDir'."
    exit 1
}
if (-not (Test-Path -LiteralPath $iaMain)) {
    Write-Fallo "No se encontro ia-service\app\main.py en '$iaDir'."
    exit 1
}
if (-not (Test-Path -LiteralPath $pythonIa)) {
    Write-Fallo "No existe el entorno virtual de ia-service:"
    Write-Fallo "  $pythonIa"
    Write-Fallo "Crealo con (desde ia-service):"
    Write-Fallo '  py -3.11 -m venv .venv'
    Write-Fallo '  .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}

# ---------------------------------------------------------------------------
# 2. Comprobar variables de vision en backend/.env (sin mostrar valores)
# ---------------------------------------------------------------------------
$backendEnv = Join-Path $backendDir '.env'
if (-not (Test-Path -LiteralPath $backendEnv)) {
    Write-Aviso "No existe backend\.env. Copia backend\.env.example y define las variables."
} else {
    $lineas = Get-Content -LiteralPath $backendEnv
    foreach ($var in @('VISION_IA_URL', 'VISION_IA_KEY')) {
        $coincide = $lineas | Where-Object { $_ -match "^\s*$var\s*=\s*(.+)$" } | Select-Object -First 1
        $valor = $null
        if ($coincide -and $coincide -match "^\s*$var\s*=\s*(.+)$") { $valor = $Matches[1].Trim().Trim('"').Trim("'") }
        if ([string]::IsNullOrWhiteSpace($valor)) {
            Write-Aviso "backend\.env no define $var (o esta vacio)."
        }
    }
}

# ---------------------------------------------------------------------------
# 3. Puerto 8000: reutilizar si es nuestro ia-service, error si es otro
# ---------------------------------------------------------------------------
$iaYaCorre = $false
$ocupado    = $false

try {
    $salud = Invoke-RestMethod -Uri "$iaUrl/vision/health" -TimeoutSec 3 -ErrorAction Stop
    if ($salud -is [string] -or $salud.model -or $salud.modelLoaded -ne $null) {
        $iaYaCorre = $true
    }
} catch {
    $ocupado = $null -ne (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

if ($iaYaCorre) {
    Write-Paso "ia-service ya esta ejecutandose en el puerto 8000 (se reutiliza)."
    Write-Host ("    modelLoaded={0} | model={1} | version={2} | device={3}" -f `
        $salud.modelLoaded, $salud.model, $salud.modelVersion, $salud.device) -ForegroundColor DarkGray
} elseif ($ocupado) {
    Write-Fallo "El puerto 8000 esta ocupado por otro proceso que no responde /vision/health."
    Write-Fallo "No se mato nada. Cierra el proceso que lo ocupa o cambia el puerto de ia-service."
    exit 1
}

# ---------------------------------------------------------------------------
# 4. Arrancar ia-service en una ventana PowerShell nueva
# ---------------------------------------------------------------------------
$procesoIa = $null

if (-not $iaYaCorre) {
    Write-Paso "Arrancando ia-service (YOLO11n) en una ventana nueva..."
    $argumentos = @(
        '-NoExit', '-NoLogo',
        '-Command',
        "Set-Location -LiteralPath '$iaDir'; " +
        "Write-Host 'ia-service RepuestoPro - YOLO11n (Ctrl+C para detener)' -ForegroundColor Cyan; " +
        "& '$pythonIa' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1"
    )
    $procesoIa = Start-Process -FilePath 'powershell.exe' -ArgumentList $argumentos -PassThru
    Write-Host "    ventana IA abierta (pid $($procesoIa.Id))" -ForegroundColor DarkGray
    Start-Sleep -Seconds 2
}

# ---------------------------------------------------------------------------
# 5. Backend Node en la terminal actual
# ---------------------------------------------------------------------------
Write-Paso "Arrancando backend Node en esta terminal (Ctrl+C para detener)..."
try {
    Push-Location -LiteralPath $backendDir
    npm run dev:backend
} finally {
    Pop-Location
    if ($null -ne $procesoIa) {
        Write-Host ''
        Write-Aviso "Cerrando la ventana de ia-service (pid $($procesoIa.Id))..."
        Stop-Process -Id $procesoIa.Id -Force -ErrorAction SilentlyContinue
    }
}
