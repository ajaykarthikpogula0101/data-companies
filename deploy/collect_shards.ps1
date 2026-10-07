<#
.SYNOPSIS
  Pull every VM's shard CSV down to Windows and merge them into one file.

.DESCRIPTION
  Safe to run mid-run: each shard CSV is complete-as-of-now, so this gives you a
  partial merged result at any point. Re-run it at the end for the final file.

.EXAMPLE
  .\deploy\collect_shards.ps1 -Ips 20.219.9.66,<ip2>,<ip3>,<ip4>,<ip5> -Merge
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string[]]$Ips,
  [int]$ShardCount = 5,
  [string]$Key  = "C:\Users\Ajay karthik pogula\Downloads\vm1-50000_key.pem",
  [string]$User = "azureuser",
  [string]$OutDir = "shards",
  [string]$Merged = "merged_all.csv",
  [switch]$Merge
)

# Continue, not Stop: ssh writes warnings and connection errors to stderr, which
# PowerShell turns into a terminating error under Stop -- one unreachable VM
# would abandon the other four.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

# Ask each VM what its output file is called -- it is named after the machine,
# so the five files never collide once they are all in one folder.
$findOutput = "ls -1t /opt/job_scraper/output/*shard*.csv 2>/dev/null | head -1"

$results = @()
foreach ($ip in $Ips) {
  $vm = "$User@$ip"
  Write-Host "`n--- $ip" -ForegroundColor Cyan

  # Two attempts: a loaded VM often resets the first connection.
  $remotePath = ""
  foreach ($attempt in 1, 2) {
    $info = @(& ssh -i "$Key" -o ConnectTimeout=25 -o StrictHostKeyChecking=accept-new `
                   $vm $findOutput 2>$null)
    if ($info.Count -gt 0 -and "$($info[0])".Trim()) { $remotePath = "$($info[0])".Trim(); break }
    if ($attempt -eq 1) { Start-Sleep -Seconds 5 }
  }
  if (-not $remotePath) {
    Write-Host "    not reachable right now -- skipped (retry later)" -ForegroundColor Yellow
    $results += [pscustomobject]@{ IP = $ip; File = "-"; MB = 0; Status = "unreachable" }
    continue
  }

  $name = Split-Path -Leaf $remotePath
  Write-Host "    file: $name"
  & scp -i "$Key" -o ConnectTimeout=25 "${vm}:$remotePath" (Join-Path $OutDir $name) 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "    download failed -- retrying once" -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    & scp -i "$Key" -o ConnectTimeout=25 "${vm}:$remotePath" (Join-Path $OutDir $name) 2>$null
  }
  $local = Join-Path $OutDir $name
  if (Test-Path $local) {
    $mb = [Math]::Round((Get-Item $local).Length / 1MB, 1)
    Write-Host ("    downloaded {0} MB" -f $mb) -ForegroundColor Green
    $results += [pscustomobject]@{ IP = $ip; File = $name; MB = $mb; Status = "ok" }
  } else {
    Write-Host "    download failed" -ForegroundColor Red
    $results += [pscustomobject]@{ IP = $ip; File = $name; MB = 0; Status = "failed" }
  }
}

Write-Host ""
$results | Format-Table -AutoSize

Get-ChildItem $OutDir -Filter "*shard*.csv" |
  Select-Object Name, @{n = "MB"; e = { [Math]::Round($_.Length / 1MB, 1) } }, LastWriteTime |
  Format-Table -AutoSize

if ($Merge) {
  Write-Host "`nmerging..." -ForegroundColor Cyan
  & python "deploy\merge_shards.py" "$OutDir\*shard*.csv" -o $Merged
}
