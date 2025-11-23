$ErrorActionPreference = "SilentlyContinue"

$services = @(
    "cryptoflux-postgres",
    "cryptoflux-postgres-dr",
    "cryptoflux-ext_api",
    "cryptoflux-trading_data",
    "cryptoflux-liquidity_calculator",
    "cryptoflux-trading_ui",
    "cryptoflux-data_ingestion_service",
    "cryptoflux-dr_sync",
    "cryptoflux-dozzle"
)

$logFile = "C:\Users\rssch\Downloads\CryptoFlux\CryptoFlux\docker_monitor.log"

Write-Host "Monitoring ${($services -join ', ')}" -ForegroundColor Cyan
Write-Host "Logging to $logFile" -ForegroundColor Cyan

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    foreach ($service in $services) {
        # Skip Dozzle health check (it has no built-in health)
        if ($service -eq "cryptoflux-dozzle") {
            continue
        }

        $status = docker inspect --format '{{.State.Status}}' $service 2>$null

        if ($status -ne "running") {
            $msg = "[$timestamp] ALERT: $service stopped (Status: $status)"
            Write-Host $msg -ForegroundColor Red
            Add-Content -Path $logFile -Value $msg
            continue
        }

        $health = docker inspect --format '{{.State.Health.Status}}' $service 2>$null

        # Only alert if health is explicitly bad (ignore empty or 'starting')
        if (($health -ne "healthy") -and ($health -ne "starting") -and ($health -ne "")) {
            $msg = "[$timestamp] ALERT: $service unhealthy (Health: $health)"
            Write-Host $msg -ForegroundColor Yellow
            Add-Content -Path $logFile -Value $msg
        } else {
            # Uncomment if you want "OK" lines:
            # Write-Host "[$timestamp] OK: $service ($status/$health)" -ForegroundColor Green
        }
    }

    Start-Sleep -Seconds 60
}
