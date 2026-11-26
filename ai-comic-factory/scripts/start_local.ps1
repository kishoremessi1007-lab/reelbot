$root = "d:\college\auto reel\ai-comic-factory"
Write-Host "Starting AI Comic Factory Backend (Port 8000) and Frontend (Port 5173)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\.venv\Scripts\uvicorn.exe backend.api.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
