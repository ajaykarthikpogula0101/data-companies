# VM setup — 20.219.9.66

Key: `C:\Users\Ajay karthik pogula\Downloads\vm1-50000_key.pem`  (contains a space — always quote it)
Host: `azureuser@20.219.9.66`

Run steps 1–4 in **PowerShell on Windows**, from `D:\data_companies`.
Steps 5–8 run **on the VM**.

---

## 1. Fix the key permissions, confirm SSH

```powershell
$KEY = "C:\Users\Ajay karthik pogula\Downloads\vm1-50000_key.pem"
$VM  = "azureuser@20.219.9.66"

icacls "$KEY" /inheritance:r
icacls "$KEY" /grant:r "$($env:USERNAME):(R)"

ssh -i "$KEY" -o StrictHostKeyChecking=accept-new $VM "hostname; nproc; free -g | head -2; df -h / | tail -1"
```

Note the vCPU / RAM numbers it prints — step 6 sizes the worker counts from them.

---

## 2. Bootstrap the VM (one script, idempotent)

```powershell
cd D:\data_companies

scp -i "$KEY" deploy\azure_ubuntu_setup.sh $VM":~/"
ssh -i "$KEY" $VM "sudo bash ~/azure_ubuntu_setup.sh"
```

Takes 5–10 minutes (apt packages + the ~250 MB Camoufox browser build). Safe to
re-run if it is interrupted. It creates the `scraper` user, `/opt/job_scraper`
with a venv, installs `camoufox[geoip]` and fetches the browser, turns on
systemd-resolved DNS caching with 1.1.1.1 / 8.8.8.8 / 9.9.9.9 fallback, adds a
4 GB swapfile, and writes `/opt/job_scraper/.env.scraper`.

---

## 3. Ship the code

`node_modules`, `.venv` and `.browser_cache` must **not** be copied —
`node_modules` holds the Windows-only `impit-win32-x64-msvc` binary.

```powershell
ssh -i "$KEY" $VM "mkdir -p /tmp/deploy/deploy"

scp -i "$KEY" -r job_scraper $VM":/tmp/deploy/"
scp -i "$KEY" run_all.py run_smoke_test.py test_job_scraper_offline.py `
              test_bad_websites.py requirements.txt $VM":/tmp/deploy/"
scp -i "$KEY" deploy\preflight.py deploy\check_output.py deploy\run_shard.sh `
              deploy\job-scraper.service $VM":/tmp/deploy/deploy/"

ssh -i "$KEY" $VM @'
  sudo rsync -a /tmp/deploy/ /opt/job_scraper/
  sudo cp /opt/job_scraper/deploy/run_shard.sh /opt/job_scraper/run_shard.sh
  sudo chown -R scraper:scraper /opt/job_scraper
  sudo chmod +x /opt/job_scraper/run_shard.sh
  sudo -u scraper /opt/job_scraper/.venv/bin/pip install -q -r /opt/job_scraper/requirements.txt
  ls -l /opt/job_scraper
'@
```

---

## 4. Ship the input data

```powershell
# full dataset (37 MB, 405,210 companies)
scp -i "$KEY" data_7.7m_405k.csv $VM":/tmp/"
# the 999-row smoke input, handy for a quick check
scp -i "$KEY" smoke_test_input.xlsx $VM":/tmp/"

ssh -i "$KEY" $VM @'
  sudo mkdir -p /opt/job_scraper/data
  sudo mv /tmp/data_7.7m_405k.csv /tmp/smoke_test_input.xlsx /opt/job_scraper/data/
  sudo chown -R scraper:scraper /opt/job_scraper/data
  ls -lh /opt/job_scraper/data
'@
```

---

## 5. Log in and verify (on the VM)

```powershell
ssh -i "$KEY" $VM
```

```bash
sudo -u scraper bash -lc '
  set -a; . /opt/job_scraper/.env.scraper; set +a
  cd /opt/job_scraper
  .venv/bin/python test_job_scraper_offline.py     # expect 101 passed
  .venv/bin/python test_bad_websites.py            # expect 17 passed
  .venv/bin/python deploy/preflight.py             # deps, camoufox, DNS, live render
'
```

`preflight.py` exits non-zero and names what is broken. Search-engine failures
are warnings; a failed Greenhouse API call or a failed live Camoufox render is
critical — do not start the full run until both pass.

---

## 6. Point the config at the real input and size the workers

```bash
sudo -u scraper tee -a /opt/job_scraper/.env.scraper >/dev/null <<'EOF'

# --- full dataset ---
JOB_SCRAPER_INPUT=/opt/job_scraper/data/data_7.7m_405k.csv
JOB_SCRAPER_OUTPUT=/opt/job_scraper/output/all_companies.csv
EOF

# then set the two worker counts to match this VM (values from step 1):
#   2 vCPU /  8 GB  ->  JOB_SCRAPER_WORKERS=8   JOB_SCRAPER_BROWSER_WORKERS=2
#   4 vCPU / 16 GB  ->  JOB_SCRAPER_WORKERS=16  JOB_SCRAPER_BROWSER_WORKERS=4
#   8 vCPU / 32 GB  ->  JOB_SCRAPER_WORKERS=32  JOB_SCRAPER_BROWSER_WORKERS=8
sudo -u scraper sed -i \
  -e 's/^JOB_SCRAPER_WORKERS=.*/JOB_SCRAPER_WORKERS=16/' \
  -e 's/^JOB_SCRAPER_BROWSER_WORKERS=.*/JOB_SCRAPER_BROWSER_WORKERS=4/' \
  /opt/job_scraper/.env.scraper

grep -iv proxy /opt/job_scraper/.env.scraper   # confirm what it now says
```

Each Camoufox worker is a full Firefox: ~700 MB RAM and ~0.5 vCPU. Over-setting
`JOB_SCRAPER_BROWSER_WORKERS` is the one setting that will OOM the box.

---

## 7. Throughput probe (2,000 companies) before the full run

```bash
sudo -u scraper bash -lc '
  set -a; . /opt/job_scraper/.env.scraper; set +a
  cd /opt/job_scraper
  nohup .venv/bin/python run_all.py --limit 2000 \
        --output /opt/job_scraper/output/probe_2000.csv \
        > logs/probe.out 2>&1 &
  echo started'

tail -f /opt/job_scraper/logs/probe.out
```

When it finishes, read the tail: `companies/min`, the `dns` line, and the
`engines` line. Then:

```bash
sudo -u scraper /opt/job_scraper/.venv/bin/python \
  /opt/job_scraper/deploy/check_output.py --file /opt/job_scraper/output/probe_2000.csv
```

At 8–11 companies/min one VM is ~31 days for 405 k, so plan on 6 VMs (~5 days).
If `engines` shows several engines benched, lower `JOB_SCRAPER_SEARCH_BUDGET`
(default 5) or stagger the shard start times.

---

## 8. Full run

Foreground / detached:

```bash
sudo -u scraper bash -lc '
  cd /opt/job_scraper && SHARD_INDEX=0 SHARD_COUNT=6 nohup ./run_shard.sh \
    > logs/shard0.out 2>&1 & echo started'
```

Or as a managed service that survives reboots and restarts on failure:

```bash
sudo tee -a /opt/job_scraper/.env.scraper >/dev/null <<'EOF'
SHARD_INDEX=0
SHARD_COUNT=6
EOF

sudo cp /opt/job_scraper/deploy/job-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now job-scraper
journalctl -u job-scraper -f
```

This VM is shard 0. Give each additional VM the same setup with
`SHARD_INDEX=1..5`; the slices are contiguous and non-overlapping.

Monitor:

```bash
watch -n 60 'wc -l /opt/job_scraper/output/shard_0_of_6.csv; free -g | head -2; \
             ls /opt/job_scraper/logs'
sudo -u scraper /opt/job_scraper/.venv/bin/python \
  /opt/job_scraper/deploy/check_output.py --file /opt/job_scraper/output/shard_0_of_6.csv --watch
```

Stop / resume — resume is on by default, so a restart picks up where it stopped:

```bash
sudo systemctl stop job-scraper
sudo systemctl start job-scraper
```

Pull the result back to Windows:

```powershell
scp -i "$KEY" $VM":/opt/job_scraper/output/shard_0_of_6.csv" D:\data_companies\
```
