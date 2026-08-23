# PowerShell local setup for OmniView demo
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Write-Host "==> Starting Postgres + Redis"
docker compose up -d

Write-Host "==> Waiting for Postgres"
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
  docker compose exec -T postgres pg_isready -U omniview -d omniview 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $ready = $true; break }
  Start-Sleep -Seconds 2
}
if (-not $ready) { throw "Postgres not ready" }

if (-not (Test-Path .venv)) {
  python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt

Write-Host "==> Seed"
Push-Location backend
& ..\.venv\Scripts\python.exe -m app.seed
Pop-Location

Write-Host "==> Frontend deps"
Push-Location frontend
npm install
Pop-Location

Write-Host @"

Ready. Run three terminals:

  1) .\.venv\Scripts\Activate.ps1; cd backend; uvicorn app.main:app --reload --port 8000
  2) .\.venv\Scripts\Activate.ps1; python worker\main.py
  3) cd frontend; npm run dev

Then open http://localhost:5173
"@
