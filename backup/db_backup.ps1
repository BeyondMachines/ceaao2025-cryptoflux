<#
===============================================================================
 CryptoFlux – PostgreSQL Backup Script (Windows PowerShell)
===============================================================================
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("backup", "restore")]
    [string]$Action,

    [string]$BackupFile
)

$container = "cryptoflux-postgres"
$backupDir = "backups"
$timestamp = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")

if (!(Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

switch ($Action) {

    # ----------------------------------------------------------
    # BACKUP MODE
    # ----------------------------------------------------------
    "backup" {
        Write-Host "Creating PostgreSQL backup from container: $container"
        $fileName = "cryptoflux_backup_$timestamp.sql"
        $filePath = Join-Path $backupDir $fileName

        docker exec $container pg_dump -U cryptouser -d cryptoflux > $filePath

        if ((Test-Path $filePath) -and ((Get-Item $filePath).Length -gt 0)) {
            Write-Host "[SUCCESS] Backup saved to $filePath"
        } else {
            Write-Host "[ERROR] Backup failed!"
        }
        break
    }

    # ----------------------------------------------------------
    # RESTORE MODE
    # ----------------------------------------------------------
    "restore" {
        if (-not $BackupFile) {
            Write-Host "Usage: .\db_backup.ps1 restore <file.sql>"
            exit 1
        }

        if (!(Test-Path $BackupFile)) {
            Write-Host "Backup file not found: $BackupFile"
            exit 1
        }

        Write-Host "Restoring database from $BackupFile..."
        Get-Content -Raw $BackupFile | docker exec -i $container psql -U cryptouser -d cryptoflux

        Write-Host "[SUCCESS] Database restored successfully."
        break
    }
}
