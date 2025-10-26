# Server Manager Launch Script

Write-Host "Starting Server Manager..." -ForegroundColor Cyan

# Check if venv exists
if (-Not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Running setup..." -ForegroundColor Yellow
    .\setup.ps1
}

# Activate venv and run
& .\.venv\Scripts\Activate.ps1
python main.py
