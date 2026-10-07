<#
.SYNOPSIS
  Set up one Azure VM to run its shard of the full 405,210-company job scrape.

.DESCRIPTION
  Run this once per VM from D:\data_companies, changing -Ip and -ShardIndex.
  Every step is idempotent: re-run it after a failure and it picks up where it
  stopped. Nothing here is a smoke test -- step 8 starts the real run over this
  VM's slice of the whole dataset.

.EXAMPLE
  .\deploy\setup_vm.ps1 -Ip 20.219.9.66 -ShardIndex 0 -Start
  .\deploy\setup_vm.ps1 -Ip <vm2-ip>   -ShardIndex 1 -Start
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Ip,
  [Parameter(Mandatory = $true)][ValidateRange(0, 63)][int]$ShardIndex,
  [int]$ShardCount = 5,
  [string]$Key  = "C:\Users\Ajay karthik pogula\Downloads\vm1-50000_key.pem",
  [string]$User = "azureuser",
  [string]$DataFile = "data_7.7m_405k.csv",
  [string]$VmName = "",        # output file prefix; default: the VM's hostname
  [int]$Workers = 0,           # 0 = size automatically from the VM's vCPU/RAM
  [int]$BrowserWorkers = 0,
  [switch]$SkipBootstrap,
  [switch]$SkipCode,
  [switch]$SkipData,
  [switch]$SkipTests,
  [switch]$Start               # install the systemd service and begin the run
)

$ErrorActionPreference = "Stop"
if ($ShardIndex -ge $ShardCount) { throw "-ShardIndex must be 0..$($ShardCount - 1)" }

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$VM = "$User@$Ip"
$APP = "/opt/job_scraper"

function Step($n, $text) { Write-Host "`n=== $n. $text" -ForegroundColor Cyan }
# Getting a multi-line script to bash intact is the fiddly part on Windows.
# Here-strings are CRLF, and PowerShell appends its own CRLF when piping into a
# native command, so bash ends up with $'echo\r': command not found. Encoding the
# script as base64 and decoding it on the VM avoids stdin, quoting and line
# endings altogether -- base64 is only A-Z a-z 0-9 + / =, all safe in a shell.
function ConvertTo-Unix([string]$text) {
  return ($text -replace "`r`n", "`n" -replace "`r", "`n")
}

function New-RemoteCommand([string]$script, [hashtable]$vars = @{}) {
  $clean  = ConvertTo-Unix $script
  $b64    = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($clean))
  $prefix = ($vars.GetEnumerator() | ForEach-Object { "$($_.Key)='$($_.Value)'" }) -join ' '
  return "echo $b64 | base64 -d | $prefix bash"
}

function Invoke-Remote([string]$script, [hashtable]$vars = @{}) {
  & ssh -i "$Key" $VM (New-RemoteCommand $script $vars)
  if ($LASTEXITCODE -ne 0) { throw "remote step failed (exit $LASTEXITCODE)" }
}

Write-Host "repo      : $Root"
Write-Host "vm        : $VM"
Write-Host "shard     : $ShardIndex of $ShardCount (interleave)"
Write-Host "input     : $DataFile"

# ---------------------------------------------------------------------------
Step 1 "Lock down the .pem permissions (OpenSSH refuses a world-readable key)"
& icacls "$Key" /inheritance:r | Out-Null
& icacls "$Key" /grant:r "$($env:USERNAME):(R)" | Out-Null
Write-Host "ok"

# ---------------------------------------------------------------------------
Step 2 "Confirm SSH and read the VM's size"
$probeScript = @'
hostname -s 2>/dev/null || hostname
nproc
awk '/MemTotal/{printf "%d\n", $2/1024/1024}' /proc/meminfo
df -BG --output=avail / | tail -1 | tr -dc '0-9'; echo
'@
$probe = @(& ssh -i "$Key" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 $VM (New-RemoteCommand $probeScript))
if ($LASTEXITCODE -ne 0) { throw "cannot ssh to $VM -- check the IP, the NSG's port 22 rule, and that the VM is running" }
$hostName = "$($probe[0])".Trim()
$vcpu = [int]$probe[1]; $ramGB = [int]$probe[2]; $diskGB = [int]$probe[3]
if (-not $VmName) { $VmName = if ($hostName) { $hostName } else { "vm$($ShardIndex + 1)" } }
Write-Host "hostname=$hostName  vCPU=$vcpu  RAM=${ramGB}GB  free disk=${diskGB}GB"
Write-Host "-> output file: ${VmName}_shard_${ShardIndex}_of_${ShardCount}.csv"

# Sizing is driven by MEMORY, not vCPU. Measured on a live 16GB run: 2 browsers
# plus 10 HTTP workers sits at ~5.8GB. Overshooting does not merely slow things
# down -- the machine starts swapping, throughput collapses, and sshd stops
# answering, which is how three days of this run were lost.
if ($Workers -eq 0) {
  $Workers = [Math]::Min($vcpu * 3, [Math]::Max(6, $ramGB))
}
if ($BrowserWorkers -eq 0) {
  # ~1.5GB per Firefox, ~3GB for everything else.
  $byMemory = [int](($ramGB - 3) / 2.5)
  $BrowserWorkers = [Math]::Max(1, [Math]::Min($byMemory, [int]($vcpu / 2)))
  # Under 12GB there is no headroom for a second browser once page content and
  # the 405k-row input are in memory.
  if ($ramGB -lt 12) { $BrowserWorkers = 1 }
}
if ($ramGB -lt 12) {
  Write-Warning ("{0}GB RAM -- low-memory SKU (D4als and similar). Using {1} workers / {2} browser to avoid swapping." -f $ramGB, $Workers, $BrowserWorkers)
}
Write-Host "-> JOB_SCRAPER_WORKERS=$Workers  JOB_SCRAPER_BROWSER_WORKERS=$BrowserWorkers"
if ($diskGB -lt 40) { Write-Warning "less than 40GB free: the browser cache and output CSV will grow" }

# ---------------------------------------------------------------------------
if (-not $SkipBootstrap) {
  Step 3 "Bootstrap the VM (packages, venv, Camoufox, DNS cache, swap) -- 5-10 min"
  & scp -i "$Key" "deploy\azure_ubuntu_setup.sh" "${VM}:~/azure_ubuntu_setup.sh"
  if ($LASTEXITCODE -ne 0) { throw "scp of azure_ubuntu_setup.sh failed" }
  Invoke-Remote "sed -i 's/\r`$//' ~/azure_ubuntu_setup.sh && sudo bash ~/azure_ubuntu_setup.sh"
} else { Step 3 "Bootstrap skipped" }

# ---------------------------------------------------------------------------
if (-not $SkipCode) {
  Step 4 "Copy the code (never node_modules / .venv / .browser_cache)"
  Invoke-Remote 'rm -rf /tmp/deploy; mkdir -p /tmp/deploy/deploy'

  # Copy job_scraper without __pycache__ or the .backup/.pre_reliability_fix
  # snapshots. The staging folder is unique per run: a shared one is still held
  # open by the previous VM's scp when two setups overlap, and deleting it fails
  # with "the process cannot access the file".
  $stage = Join-Path $env:TEMP ("job_scraper_stage_" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
  New-Item -ItemType Directory -Path $stage | Out-Null
  Get-ChildItem "job_scraper\*.py" -File | Copy-Item -Destination $stage

  & scp -i "$Key" -r "$stage" "${VM}:/tmp/deploy/job_scraper"
  if ($LASTEXITCODE -ne 0) { throw "scp of job_scraper failed" }
  & scp -i "$Key" run_all.py run_smoke_test.py test_job_scraper_offline.py `
        test_bad_websites.py requirements.txt "${VM}:/tmp/deploy/"
  if ($LASTEXITCODE -ne 0) { throw "scp of top-level files failed" }
  & scp -i "$Key" "deploy\preflight.py" "deploy\check_output.py" "deploy\run_shard.sh" `
        "deploy\job-scraper.service" "${VM}:/tmp/deploy/deploy/"
  if ($LASTEXITCODE -ne 0) { throw "scp of deploy files failed" }

  Invoke-Remote @'
set -e
sudo rsync -a --delete-after /tmp/deploy/job_scraper/ /opt/job_scraper/job_scraper/
sudo rsync -a /tmp/deploy/ /opt/job_scraper/ --exclude job_scraper
sudo cp /opt/job_scraper/deploy/run_shard.sh /opt/job_scraper/run_shard.sh
# Strip any Windows CRLF that survived the copy -- bash treats a trailing \r as
# part of the command and fails with "$'\r': command not found".
sudo find /opt/job_scraper -maxdepth 2 -name '*.sh' -exec sed -i 's/\r$//' {} +
sudo chown -R scraper:scraper /opt/job_scraper
sudo chmod +x /opt/job_scraper/run_shard.sh
sudo -u scraper /opt/job_scraper/.venv/bin/pip install -q -r /opt/job_scraper/requirements.txt
echo "--- /opt/job_scraper"
ls /opt/job_scraper
echo "--- job_scraper package: $(ls /opt/job_scraper/job_scraper/*.py 2>/dev/null | wc -l) modules"
# Run from the app directory: the package is /opt/job_scraper/job_scraper, so it is
# only importable when /opt/job_scraper is on sys.path.
cd /opt/job_scraper
sudo -u scraper env PYTHONPATH=/opt/job_scraper /opt/job_scraper/.venv/bin/python \
  -c "import job_scraper.pipeline, job_scraper.company, job_scraper.websearch; print('imports ok')"
'@
  Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
} else { Step 4 "Code copy skipped" }

# ---------------------------------------------------------------------------
if (-not $SkipData) {
  Step 5 "Copy the full input dataset (skipped if already there and the same size)"
  if (-not (Test-Path $DataFile)) { throw "$DataFile not found in $Root" }
  $localSize = (Get-Item $DataFile).Length
  $remoteSize = (& ssh -i "$Key" $VM "stat -c %s $APP/data/$(Split-Path -Leaf $DataFile) 2>/dev/null || echo 0")
  if ([int64]$remoteSize -eq $localSize) {
    Write-Host "already present ($localSize bytes) -- skipping"
  } else {
    & scp -i "$Key" $DataFile "${VM}:/tmp/"
    if ($LASTEXITCODE -ne 0) { throw "scp of $DataFile failed" }
    $moveData = @'
set -e
sudo mkdir -p /opt/job_scraper/data /opt/job_scraper/output /opt/job_scraper/logs
sudo mv "/tmp/$DATA_NAME" /opt/job_scraper/data/
sudo chown -R scraper:scraper /opt/job_scraper/data /opt/job_scraper/output /opt/job_scraper/logs
ls -lh /opt/job_scraper/data
'@
    Invoke-Remote $moveData @{ DATA_NAME = (Split-Path -Leaf $DataFile) }
  }
} else { Step 5 "Data copy skipped" }

# ---------------------------------------------------------------------------
Step 6 "Write this VM's configuration"
$writeEnv = @'
set -e
E=/opt/job_scraper/.env.scraper
sudo mkdir -p /opt/job_scraper/data /opt/job_scraper/output /opt/job_scraper/logs
sudo chown -R scraper:scraper /opt/job_scraper/output /opt/job_scraper/logs
sudo touch "$E"; sudo chown scraper:scraper "$E"; sudo chmod 600 "$E"
set_env() {
  if sudo grep -q "^$1=" "$E"; then sudo sed -i "s|^$1=.*|$1=$2|" "$E";
  else echo "$1=$2" | sudo tee -a "$E" >/dev/null; fi
}
set_env JOB_SCRAPER_BASE_DIR       /opt/job_scraper
set_env JOB_SCRAPER_INPUT          /opt/job_scraper/data/$DATA_NAME
set_env VM_NAME                    $VM_NAME
set_env JOB_SCRAPER_OUTPUT         /opt/job_scraper/output/${VM_NAME}_shard_${SHARD_INDEX}_of_${SHARD_COUNT}.csv
set_env JOB_SCRAPER_LOG            /opt/job_scraper/logs/scraper.log
set_env JOB_SCRAPER_WORKERS        $WORKERS
set_env JOB_SCRAPER_BROWSER_WORKERS $BROWSER_WORKERS
set_env JOB_SCRAPER_SHARD_MODE     interleave
set_env SHARD_INDEX                $SHARD_INDEX
set_env SHARD_COUNT                $SHARD_COUNT
set_env CAMOUFOX_HEADLESS          virtual
set_env CAMOUFOX_HUMANIZE          true
set_env PYTHONUNBUFFERED           1
sudo chown scraper:scraper "$E"
echo "--- .env.scraper ---"; sudo grep -v -i proxy "$E"
'@
Invoke-Remote $writeEnv @{
  DATA_NAME       = (Split-Path -Leaf $DataFile)
  VM_NAME         = $VmName
  SHARD_INDEX     = $ShardIndex
  SHARD_COUNT     = $ShardCount
  WORKERS         = $Workers
  BROWSER_WORKERS = $BrowserWorkers
}

# ---------------------------------------------------------------------------
if (-not $SkipTests) {
  Step 7 "Verify the install (both offline suites, then a live Camoufox render)"
  Invoke-Remote @'
set -e
sudo -u scraper bash -lc '
  set -a; . /opt/job_scraper/.env.scraper; set +a
  export PYTHONPATH=/opt/job_scraper
  cd /opt/job_scraper
  .venv/bin/python test_job_scraper_offline.py
  .venv/bin/python test_bad_websites.py
  .venv/bin/python deploy/preflight.py
'
'@
} else { Step 7 "Verification skipped" }

# ---------------------------------------------------------------------------
if ($Start) {
  Step 8 "Start the real run as a managed service"
  Invoke-Remote @'
set -e
sudo cp /opt/job_scraper/deploy/job-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now job-scraper
sleep 20
systemctl --no-pager --lines=0 status job-scraper || true
tail -n 20 /opt/job_scraper/logs/service.out.log 2>/dev/null || true
'@
  Write-Host "`nRunning. Follow it with:" -ForegroundColor Green
  Write-Host "  ssh -i `"$Key`" $VM 'journalctl -u job-scraper -f'"
} else {
  Step 8 "Not started (-Start omitted). To start the real run:"
  Write-Host "  ssh -i `"$Key`" $VM 'sudo cp $APP/deploy/job-scraper.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now job-scraper'"
}

Write-Host "`nVM $Ip ($VmName) is shard $ShardIndex of $ShardCount." -ForegroundColor Green
Write-Host "Its output file is /opt/job_scraper/output/${VmName}_shard_${ShardIndex}_of_${ShardCount}.csv"
Write-Host "The run lives on the VM. You can close PowerShell and shut down this laptop." -ForegroundColor Green
