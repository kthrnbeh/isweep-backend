$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvPath = Join-Path $scriptDir ".venv"
if (-not (Test-Path $venvPath)) {
    python -m venv .venv
}

 $venvPython = Join-Path $venvPath "Scripts\python.exe"

& $venvPython -m pip install -r requirements.txt

try {
    & $venvPython -c "import app.main"
} catch {
    Write-Error "Failed to import app.main. Ensure dependencies are installed and run from isweep-backend."
    exit 1
}

& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
