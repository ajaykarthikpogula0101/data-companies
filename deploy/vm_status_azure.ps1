<#
.SYNOPSIS
  Progress for every VM, read through Azure instead of SSH.

.DESCRIPTION
  Under full load the scrapers can starve sshd of CPU, and a status check times
  out "during banner exchange" even though the machine is working perfectly.
  This route goes through the Azure agent, which is not affected -- it always
  answers, it is just slower (about 30 seconds per VM).

  Use vm_status.ps1 for a quick look, and this when a VM will not answer.

.EXAMPLE
  .\deploy\vm_status_azure.ps1
  .\deploy\vm_status_azure.ps1 -Vms @{ "vm1-50000" = "company-super-scraper" }
#>
[CmdletBinding()]
param(
  [System.Collections.IDictionary]$Vms = [ordered]@{
    "vm1-50000" = "company-super-scraper"
    "vm2nd"     = "company-super-scraper"
    "vm3rd"     = "company-super-scraper"
    "vm4th"     = "vm4th_group"
    "vm5th"     = "company-super-scraper"
  }
)

$ErrorActionPreference = "Continue"

# Runs as root through the Azure agent, so no sudo and no SSH.
$script = @'
APP=/opt/job_scraper
E=$APP/.env.scraper
LOG=$APP/logs/scraper.log
get() { grep -m1 "^$1=" "$E" 2>/dev/null | cut -d= -f2- ; }
NAME=$(get VM_NAME); [ -z "$NAME" ] && NAME=$(hostname -s)
IDX=$(get SHARD_INDEX); CNT=$(get SHARD_COUNT)
TAIL=$(tail -n 40000 "$LOG" 2>/dev/null)
SHARE=$(printf '%s\n' "$TAIL" | grep -e "Shard .*companies" | tail -1 | sed 's/.*: \([0-9]*\) companies.*/\1/')
[ -z "$SHARE" ] && SHARE=$(grep -m1 -e "Shard .*companies" "$LOG" 2>/dev/null | sed 's/.*: \([0-9]*\) companies.*/\1/')
[ -z "$SHARE" ] && SHARE=81042
OUT=$(ls -1t $APP/output/*shard*.csv 2>/dev/null | head -1)
ROWS=0; [ -n "$OUT" ] && ROWS=$(( $(wc -l < "$OUT") - 1 )); [ "$ROWS" -lt 0 ] && ROWS=0
PROG=$(printf '%s\n' "$TAIL" | grep -o "ok=[0-9]* no_jobs=[0-9]* unreach=[0-9]* err=[0-9]* jobs=[0-9]*" | tail -1)
OK=$(echo "$PROG" | sed -n 's/.*ok=\([0-9]*\).*/\1/p'); [ -z "$OK" ] && OK=0
JOBS=$(echo "$PROG" | sed -n 's/.*jobs=\([0-9]*\).*/\1/p'); [ -z "$JOBS" ] && JOBS=0
STATE=$(systemctl is-active job-scraper 2>/dev/null || true); [ -z "$STATE" ] && STATE=none
RE=$(systemctl show job-scraper -p NRestarts --value 2>/dev/null); [ -z "$RE" ] && RE=0
LOAD=$(cut -d' ' -f1-3 /proc/loadavg)
MEM=$(free -m | awk '/Mem:/{printf "%d/%dMB", $3, $2}')
SWAP=$(free -m | awk '/Swap:/{printf "%d/%dMB", $3, $2}')
OOM=$(dmesg 2>/dev/null | grep -ci "out of memory")
echo "RESULT|$NAME|$IDX/$CNT|$ROWS|$SHARE|$OK|$JOBS|$STATE|$RE|$LOAD|$MEM|$SWAP|$OOM"
'@

$tmp = Join-Path $env:TEMP ("vmstat_" + [Guid]::NewGuid().ToString("N").Substring(0, 6) + ".sh")
($script -replace "`r`n", "`n") | Set-Content -Path $tmp -Encoding ascii -NoNewline

Write-Host ("`n=== {0} (via Azure) ===" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -ForegroundColor Cyan
$fmt = "{0,-11} {1,-5} {2,8} {3,6} {4,6} {5,9} {6,-8} {7,3} {8,-16} {9,-13} {10,-13} {11,3}"
Write-Host ($fmt -f "name", "shard", "done", "pct", "ok", "positions", "state", "re",
                    "load(1/5/15)", "memory", "swap", "oom") -ForegroundColor White

$totalDone = 0; $totalShare = 0
foreach ($name in $Vms.Keys) {
  $rg = $Vms[$name]
  $msg = & az vm run-command invoke -g $rg -n $name --command-id RunShellScript `
              --scripts "@$tmp" --query "value[0].message" -o tsv 2>$null
  $line = ($msg -split "`n" | Where-Object { $_ -like "RESULT|*" } | Select-Object -First 1)
  if (-not $line) {
    Write-Host ("{0,-11} {1}" -f $name, "no response from the Azure agent") -ForegroundColor Red
    continue
  }
  $f = $line -split '\|'
  $rows = [int]$f[3]; $share = [int]$f[4]
  $pct  = if ($share -gt 0) { "{0:N1}%" -f (100 * $rows / $share) } else { "-" }
  $color = if ($f[7] -eq "active") { "Green" } else { "Red" }
  Write-Host ($fmt -f $f[1], $f[2], $rows, $pct, $f[5], $f[6], $f[7], $f[8],
                      $f[9], $f[10], $f[11], $f[12]) -ForegroundColor $color
  if ([int]$f[12] -gt 0) {
    Write-Host "    out-of-memory kills seen -- lower JOB_SCRAPER_BROWSER_WORKERS" -ForegroundColor Yellow
  }
  $totalDone += $rows; $totalShare += $share
}

$overall = if ($totalShare -gt 0) { "{0:N1}%" -f (100 * $totalDone / $totalShare) } else { "-" }
Write-Host ($fmt -f "TOTAL", "", $totalDone, $overall, "", "", "", "", "", "", "", "") -ForegroundColor Cyan
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
