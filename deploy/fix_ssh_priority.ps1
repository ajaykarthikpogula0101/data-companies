<#
.SYNOPSIS
  Stop the scraper from starving SSH, on every VM, without needing SSH.

.DESCRIPTION
  Each VM runs 16 worker threads plus several full Firefox instances on 4 CPUs.
  At full tilt sshd cannot get scheduled in time to send its greeting, and a
  status check fails with "Connection timed out during banner exchange" even
  though the machine is fine.

  This gives the scraper a lower scheduling priority than everything else. The
  scraper still gets all the idle CPU -- which is nearly all of it -- but the
  moment sshd wants to run, it wins. Throughput cost is a few percent at most.

  Applied through the Azure agent, so it works on VMs that are currently
  refusing SSH. Each VM restarts its service, which is safe: the run resumes
  from its own output file and never repeats a company.

.EXAMPLE
  .\deploy\fix_ssh_priority.ps1
#>
[CmdletBinding()]
param(
  [System.Collections.IDictionary]$Vms = [ordered]@{
    "vm1-50000" = "company-super-scraper"
    "vm2nd"     = "company-super-scraper"
    "vm3rd"     = "company-super-scraper"
    "vm4th"     = "vm4th_group"
    "vm5th"     = "company-super-scraper"
  },
  [switch]$NoRestart
)

$ErrorActionPreference = "Continue"

$script = @'
set -e
mkdir -p /etc/systemd/system/job-scraper.service.d
cat > /etc/systemd/system/job-scraper.service.d/10-priority.conf <<EOF
[Service]
# Lower priority than sshd and the Azure agent, so the box stays reachable
# under full load. The scraper still gets every otherwise-idle cycle.
Nice=10
CPUWeight=40
IOWeight=40
EOF
systemctl daemon-reload
echo "priority drop-in installed"
RESTART_FLAG
systemctl is-active job-scraper
renice -n 10 -p $(pgrep -f run_all.py | head -1) 2>/dev/null || true
uptime
'@

foreach ($name in $Vms.Keys) {
  $rg = $Vms[$name]
  Write-Host "`n===== $name" -ForegroundColor Cyan

  $body = if ($NoRestart) {
    $script -replace 'RESTART_FLAG', 'echo "not restarting -- change applies on next restart"'
  } else {
    $script -replace 'RESTART_FLAG', 'systemctl restart job-scraper; sleep 8'
  }

  $tmp = Join-Path $env:TEMP ("prio_" + [Guid]::NewGuid().ToString("N").Substring(0, 6) + ".sh")
  ($body -replace "`r`n", "`n") | Set-Content -Path $tmp -Encoding ascii -NoNewline

  & az vm run-command invoke -g $rg -n $name --command-id RunShellScript `
       --scripts "@$tmp" --query "value[0].message" -o tsv

  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

Write-Host "`nDone. Try .\deploy\vm_status.ps1 again -- SSH should answer now." -ForegroundColor Green
