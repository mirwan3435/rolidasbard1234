# Menjalankan dashboard (backend + frontend). Tidak menyalakan sistem trading.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $env:DASHBOARD_MODE) { $env:DASHBOARD_MODE = "mock" }
$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "venv tidak ditemukan. Dari folder proyek: py -3.12 -m venv venv"
}
Write-Host "Mode: $env:DASHBOARD_MODE"
Write-Host "Backend  http://127.0.0.1:8765"
Write-Host "Frontend http://127.0.0.1:5173"
$backend = Start-Process -FilePath $Python -ArgumentList @("-m","uvicorn","dashboard_api.main:app","--host","127.0.0.1","--port","8765") -WorkingDirectory $Root -PassThru
$frontend = Start-Process -FilePath "npm.cmd" -ArgumentList @("run","dev","--","--host","127.0.0.1","--port","5173") -WorkingDirectory (Join-Path $Root "dashboard_ui") -PassThru
Write-Host "Backend PID $($backend.Id) | Frontend PID $($frontend.Id)"
Write-Host "Buka http://127.0.0.1:5173"
Write-Host "Tutup jendela uvicorn dan Vite untuk berhenti. Sistem trading tidak ikut mati."
