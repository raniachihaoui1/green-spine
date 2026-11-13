# Creates the gsenv environment with the exact tested versions (Windows).
# Usage:  .\setup_gsenv.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
py -3.13 -m venv gsenv
if ($LASTEXITCODE -ne 0) { throw "Python 3.13 not found. Install it from https://www.python.org/downloads/" }
.\gsenv\Scripts\python.exe -m pip install --upgrade pip
.\gsenv\Scripts\python.exe -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Package install failed." }
Write-Host "`ngsenv is ready. Activate it with:  .\gsenv\Scripts\Activate.ps1"
Write-Host "Then run the app with:            streamlit run app.py"
