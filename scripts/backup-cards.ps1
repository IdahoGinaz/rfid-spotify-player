# Copies the card mappings from the jukebox to OneDrive. Run on your PC:
#   .\scripts\backup-cards.ps1
# Does not copy the Soloist API key.
param(
    [string]$Target = "jukebox@jukebox.local",
    [string]$Dest = "$env:OneDrive\Backups\jukebox"
)

New-Item -ItemType Directory -Force $Dest | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd"
$file = Join-Path $Dest "cards-$stamp.json"
scp "${Target}:~/.config/rfid-player/cards.json" $file
if ($LASTEXITCODE -eq 0) { Write-Host "Saved $file" } else { Write-Error "Backup failed" }
