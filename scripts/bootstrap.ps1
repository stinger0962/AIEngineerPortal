Write-Host "Starting local infrastructure..."
docker compose up -d postgres redis

Write-Host "Install backend dependencies with:"
Write-Host "  py -3.8 -m pip install -r backend\\requirements.txt"

Write-Host "Install frontend dependencies with:"
Write-Host "  & 'C:\\Program Files\\nodejs\\npm.cmd' install --prefix frontend"
