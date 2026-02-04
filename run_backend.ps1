$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvPath = Join-Path $scriptDir ".venv"
if (-not (Test-Path $venvPath)) {
    python -m venv .venv
}

$activatePath = Join-Path $venvPath "Scripts\Activate.ps1"
. $activatePath

pip install -r requirements.txt

try {
    python -c "import app.main"
} catch {
    Write-Error "Failed to import app.main. Ensure dependencies are installed and run from isweep-backend."
    exit 1
}

python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
