# Giai phong cac cong dev (8000 API, 3000/3001 Next). Chay tu thu muc goc repo:
#   .\stop-local.ps1
$ErrorActionPreference = "SilentlyContinue"
foreach ($port in 8000, 3000, 3001) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $owning = $_.OwningProcess
        if ($owning -gt 0) {
            $p = Get-Process -Id $owning -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host "Port $port : stopping $($p.ProcessName) (PID $owning)"
                Stop-Process -Id $owning -Force
            }
        }
    }
}
Write-Host "Done. Ports 8000, 3000, 3001 should be free (ignore TIME_WAIT)."
