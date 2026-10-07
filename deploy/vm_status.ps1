<#
.SYNOPSIS
  One table across every VM: companies processed, speed, quality, ETA.

.EXAMPLE
  .\deploy\vm_status.ps1 -Ips 20.219.9.66,172.198.74.49,4.154.0.198,20.97.218.75,20.225.48.112
  .\deploy\vm_status.ps1 -Ips 20.219.9.66 -Watch
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string[]]$Ips,
  [string]$Key  = "C:\Users\Ajay karthik pogula\Downloads\vm1-50000_key.pem",
  [string]$User = "azureuser",
  [switch]$Watch,
  [int]$EverySeconds = 300
)

$ErrorActionPreference = "Continue"

# Send the script base64-encoded: avoids stdin, quoting and CRLF entirely.
function New-RemoteCommand([string]$script) {
  $clean = $script -replace "`r`n", "`n" -replace "`r", "`n"
  $b64   = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($clean))
  return "echo $b64 | base64 -d | bash"
}

# .env.scraper is chmod 600 owned by the scraper user, so every read of it needs
# sudo -- without it the shard number comes back empty and the percentages are
# nonsense. The shard size comes from the log, which is what the run actually
# decided, rather than being recalculated here.
$remote = @'
APP=/opt/job_scraper
E=$APP/.env.scraper
get() { sudo grep -m1 "^$1=" "$E" 2>/dev/null | cut -d= -f2- ; }

IDX=$(get SHARD_INDEX)
CNT=$(get SHARD_COUNT)
NAME=$(get VM_NAME)
[ -z "$NAME" ] && NAME=$(hostname -s 2>/dev/null || hostname)
[ -z "$IDX" ] && IDX="?"
[ -z "$CNT" ] && CNT="?"

LOG=$APP/logs/scraper.log
# The log grows to hundreds of MB over a multi-day run. Scanning all of it on
# every status check takes minutes and makes the SSH call look like a hung or
# unreachable machine, so read the tail and only fall back to a full scan if the
# line is not there.
TAIL=$(sudo tail -n 40000 "$LOG" 2>/dev/null)

# A LIMIT in the config means this VM was capped to a smaller slice than its
# whole shard, and THAT is what its progress should be measured against --
# otherwise a VM that is 33% through its real workload reads as 14%.
CAP=$(get LIMIT)
case "$CAP" in (*[!0-9]*|"") CAP=0 ;; esac

SHARE=$(printf '%s\n' "$TAIL" | grep -e "Companies to process this run" | tail -1 | sed 's/.*: \([0-9]*\).*/\1/')
[ -z "$SHARE" ] && SHARE=$(printf '%s\n' "$TAIL" | grep -e "Shard .*companies" | tail -1 | sed 's/.*: \([0-9]*\) companies.*/\1/')
[ -z "$SHARE" ] && SHARE=$(sudo grep -m1 -e "Shard .*companies" "$LOG" 2>/dev/null | sed 's/.*: \([0-9]*\) companies.*/\1/')
[ -z "$SHARE" ] && SHARE=0
# The cap wins whenever it is set and smaller than the shard.
if [ "$CAP" -gt 0 ] && { [ "$SHARE" -eq 0 ] || [ "$CAP" -lt "$SHARE" ]; }; then SHARE=$CAP; fi

OUT=$APP/output/${NAME}_shard_${IDX}_of_${CNT}.csv
[ -f "$OUT" ] || OUT=$(ls -1t $APP/output/*shard*.csv 2>/dev/null | head -1)

# The output holds ONE ROW PER JOB POSTING, so a line count is NOT a company
# count -- a company with 400 postings contributes 400 lines. Count distinct
# companies properly, and the postings alongside them.
ROWS=0; POSTINGS=0
if [ -n "$OUT" ] && [ -f "$OUT" ]; then
  COUNTS=$($APP/.venv/bin/python - "$OUT" <<'PYEOF' 2>/dev/null
import csv, sys
csv.field_size_limit(10 ** 7)
companies, postings = set(), 0
with open(sys.argv[1], newline="", encoding="utf-8-sig", errors="replace") as fh:
    reader = csv.reader(fh)
    header = next(reader, None) or []
    ci = header.index("company_name") if "company_name" in header else 0
    ui = header.index("job_url") if "job_url" in header else -1
    for row in reader:
        if not row:
            continue
        if len(row) > ci:
            companies.add(row[ci])
        if ui >= 0 and len(row) > ui and row[ui].strip():
            postings += 1
print("%d %d" % (len(companies), postings))
PYEOF
)
  ROWS=$(echo "$COUNTS" | awk '{print $1+0}')
  POSTINGS=$(echo "$COUNTS" | awk '{print $2+0}')
fi

# Latest progress line: [n/m] ok=.. no_jobs=.. unreach=.. err=.. jobs=..
# These counters restart with the process, so PROC (companies done since the
# service last started) is what the speed must be measured against -- not the
# CSV row count, which survives restarts and would report a wild rate.
PROG=$(printf '%s\n' "$TAIL" | grep -o "\[[0-9]*/[0-9]*\] ok=[0-9]* no_jobs=[0-9]* unreach=[0-9]* err=[0-9]* jobs=[0-9]*" | tail -1)
PROC=$(echo "$PROG"    | sed -n 's/^\[\([0-9]*\)\/.*/\1/p');    [ -z "$PROC" ] && PROC=0
OK=$(echo "$PROG"      | sed -n 's/.*ok=\([0-9]*\).*/\1/p');      [ -z "$OK" ] && OK=0
UNREACH=$(echo "$PROG" | sed -n 's/.*unreach=\([0-9]*\).*/\1/p'); [ -z "$UNREACH" ] && UNREACH=0
JOBS=$(echo "$PROG"    | sed -n 's/.*jobs=\([0-9]*\).*/\1/p');    [ -z "$JOBS" ] && JOBS=0
RESTARTS=$(systemctl show job-scraper -p NRestarts --value 2>/dev/null); [ -z "$RESTARTS" ] && RESTARTS=0

STATE=$(systemctl is-active job-scraper 2>/dev/null || true); [ -z "$STATE" ] && STATE=none
SINCE=$(systemctl show job-scraper -p ActiveEnterTimestampMonotonic --value 2>/dev/null)
UP=$(awk '{printf "%d", $1}' /proc/uptime)
UPSEC=$(( UP - ${SINCE:-0}/1000000 )); [ "$UPSEC" -lt 1 ] && UPSEC=1
FF=$(pgrep -cf camoufox 2>/dev/null || true); [ -z "$FF" ] && FF=0
DISK=$(df -h $APP | tail -1 | awk '{print $4}')
BENCH=$(printf '%s\n' "$TAIL" | grep -c "benched" || true); [ -z "$BENCH" ] && BENCH=0
LOGMB=$(du -m "$LOG" 2>/dev/null | cut -f1); [ -z "$LOGMB" ] && LOGMB=0

echo "NAME=$NAME"
echo "IDX=$IDX"
echo "CNT=$CNT"
echo "SHARE=$SHARE"
echo "CAP=$CAP"
echo "ROWS=$ROWS"
echo "PROC=$PROC"
echo "POSTINGS=$POSTINGS"
echo "RESTARTS=$RESTARTS"
echo "OK=$OK"
echo "UNREACH=$UNREACH"
echo "JOBS=$JOBS"
echo "STATE=$STATE"
echo "UPSEC=$UPSEC"
echo "FF=$FF"
echo "DISK=$DISK"
echo "BENCH=$BENCH"
echo "LOGMB=$LOGMB"
'@

# One colour per VM so rows are easy to tell apart at a glance. No red anywhere:
# a VM that is not active is marked with "!!" in front of its IP instead, which
# reads as "look here" without looking like a failure.
$VmColours = @("Green", "Cyan", "Yellow", "Magenta", "Blue", "DarkCyan", "DarkGreen", "DarkMagenta")

function Show-Status {
  Write-Host ("`n=== {0} ===" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -ForegroundColor White
  $fmt = "{0,-15} {1,-11} {2,-5} {3,8} {4,8} {5,6} {6,7} {7,8} {8,9} {9,-8} {10,3} {11,7} {12,4} {13,6}"
  Write-Host ($fmt -f "IP", "name", "shard", "done", "target", "pct", "ok", "unreach", "positions",
                      "state", "re", "comp/min", "ffx", "eta") -ForegroundColor White

  $totalDone = 0; $totalShare = 0; $totalJobs = 0
  $slot = 0
  foreach ($ip in $Ips) {
    $rowColour = $VmColours[$slot % $VmColours.Count]
    $slot++
    # A loaded VM can miss one connection; one retry avoids reporting a machine
    # that is working perfectly well as dead.
    $out = @()
    foreach ($attempt in 1, 2) {
      $out = @(& ssh -i "$Key" -o ConnectTimeout=25 -o ServerAliveInterval=10 `
                    -o StrictHostKeyChecking=accept-new `
                    "$User@$ip" (New-RemoteCommand $remote) 2>$null)
      if ($LASTEXITCODE -eq 0 -and $out.Count -gt 0) { break }
      if ($attempt -eq 1) { Start-Sleep -Seconds 5 }
    }
    if ($out.Count -eq 0) {
      Write-Host ("{0,-15} {1}" -f ("!! " + $ip), "no answer (VM may just be busy -- try again)") `
        -ForegroundColor $rowColour
      continue
    }

    $kv = @{}
    foreach ($line in $out) {
      $bits = "$line".Trim() -split '=', 2
      if ($bits.Count -eq 2) { $kv[$bits[0]] = $bits[1] }
    }

    $rows  = [int]($kv["ROWS"]  -as [int])
    $share = [int]($kv["SHARE"] -as [int])
    $jobs  = [int]($kv["POSTINGS"] -as [int])
    if ($jobs -eq 0) { $jobs = [int]($kv["JOBS"] -as [int]) }
    $proc  = [int]($kv["PROC"]  -as [int])
    $upmin = [Math]::Max(1, [int]($kv["UPSEC"] -as [int]) / 60)
    # Speed of the CURRENT process only: rows in the CSV include everything done
    # before the last restart, so dividing those by the uptime invents a number.
    $rate  = [Math]::Round($proc / $upmin, 1)
    $pct   = if ($share -gt 0) { "{0:N1}%" -f (100 * $rows / $share) } else { "-" }
    $eta   = if ($rate -gt 0 -and $share -gt $rows) {
               "{0:N1}d" -f (($share - $rows) / $rate / 1440)
             } elseif ($share -gt 0 -and $share -le $rows) { "done" } else { "-" }

    $label = if ($kv["STATE"] -eq "active") { $ip } else { "!! " + $ip }
    Write-Host ($fmt -f $label, $kv["NAME"], "$($kv['IDX'])/$($kv['CNT'])", $rows, $share, $pct,
                        $kv["OK"], $kv["UNREACH"], $jobs, $kv["STATE"], $kv["RESTARTS"],
                        $rate, $kv["FF"], $eta) -ForegroundColor $rowColour

    if ([int]($kv["RESTARTS"] -as [int]) -gt 3) {
      Write-Host ("    service has restarted {0} times -- check: journalctl -u job-scraper -n 50" -f $kv["RESTARTS"]) -ForegroundColor DarkYellow
    }

    if ([int]($kv["BENCH"] -as [int]) -gt 200) {
      Write-Host ("    search engines benched {0} times -- consider lowering JOB_SCRAPER_SEARCH_BUDGET_NO_SITE" -f $kv["BENCH"]) -ForegroundColor DarkYellow
    }
    $totalDone += $rows; $totalShare += $share; $totalJobs += $jobs
  }

  $overall = if ($totalShare -gt 0) { "{0:N1}%" -f (100 * $totalDone / $totalShare) } else { "-" }
  Write-Host ($fmt -f "TOTAL", "", "", $totalDone, $totalShare, $overall, "", "", $totalJobs, "", "", "", "", "") -ForegroundColor White
}

if ($Watch) {
  while ($true) { Show-Status; Start-Sleep -Seconds $EverySeconds }
} else {
  Show-Status
}
