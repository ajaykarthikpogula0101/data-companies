# Azure Ubuntu VM setup — job_scraper + Camoufox

## Before you start: the Camoufox binding

`browser_fetch.py` used to do `from camoufox_js.sync_api import Camoufox` against
`camofox-browser-master/node_modules`. `camoufox-js` there is a **pure JavaScript**
package (`dist/`, `package.json` only) — Python cannot import it, so that call
raised `ImportError` on every run and stealth rendering never actually happened.

It now prefers the **PyPI `camoufox` package** (`camoufox.sync_api`) and keeps the
old path as a fallback. That is the dependency the setup script installs.

Also note `node_modules/impit-win32-x64-msvc` — a Windows-only native binary. That
`node_modules` tree is **not portable to Linux**; do not rsync it. Only install Node
on the VM if you separately want to run `camofox-browser`'s `server.js`.

---

## 1. Provision the VM

```bash
RG=rg-scraper
LOC=centralindia
VM=scraper-vm-0

az group create -n $RG -l $LOC

az vm create \
  --resource-group $RG --name $VM \
  --image Ubuntu2404 \
  --size Standard_D4as_v5 \
  --admin-username azureuser \
  --generate-ssh-keys \
  --os-disk-size-gb 128 \
  --public-ip-sku Standard

# Outbound 80/443 is open by default. No inbound rules needed beyond SSH.
az vm open-port -g $RG -n $VM --port 22
```

**Sizing.** Avoid B-series (burstable) — CPU credits run out under sustained
scraping and everything silently slows down. Each Camoufox worker is a full
Firefox: budget ~700 MB RAM and ~0.5 vCPU per browser worker, plus ~50 MB per HTTP
worker thread.

| SKU | vCPU | RAM | Suggested `JOB_SCRAPER_WORKERS` / `BROWSER_WORKERS` |
|---|---|---|---|
| `Standard_D2as_v5` | 2 | 8 GB | 8 / 2 |
| `Standard_D4as_v5` | 4 | 16 GB | 16 / 4 |
| `Standard_D8as_v5` | 8 | 32 GB | 32 / 8 |

Disk: 128 GB minimum. The Camoufox build is ~250 MB, and `.browser_cache/` plus
CSV output grow steadily on a 405 k-row job.

---

## 2. Bootstrap (one command)

```bash
scp azure_ubuntu_setup.sh azureuser@<vm-ip>:~
ssh azureuser@<vm-ip>
sudo bash azure_ubuntu_setup.sh
```

Idempotent — re-run it any time. Flags: `--with-node` (Node 22 as well),
`--skip-browser` (skip the ~250 MB Camoufox download).

It installs: build tools and Python 3 + venv; the full Firefox runtime library set
(gtk3, nss, atk, cairo/pango, egl/gbm, alsa, cups, dbus-glib, fonts) with 22.04 /
24.04 package-name differences handled; Xvfb; the Python dependencies including
`camoufox[geoip]`, `dnspython`, `pyvirtualdisplay`; the Camoufox browser build; a
4 GB swapfile; fd/socket limits; and — importantly — **systemd-resolved DNS caching
with 1.1.1.1 / 8.8.8.8 / 9.9.9.9 fallback**. Azure's platform resolver
(168.63.129.16) rate-limits under a scraper's query volume, which is a second
source of the `NameResolutionError` failures on top of the column-mapping bug.

---

## 3. Ship the code

```bash
# From D:\data_companies (Git Bash / WSL). Do NOT copy node_modules or .venv.
rsync -av --exclude '__pycache__' --exclude '.browser_cache' --exclude '.venv' \
  job_scraper/ run_smoke_test.py test_job_scraper_offline.py requirements.txt \
  preflight.py run_shard.sh \
  azureuser@<vm-ip>:/tmp/deploy/

ssh azureuser@<vm-ip> '
  sudo rsync -a /tmp/deploy/ /opt/job_scraper/ &&
  sudo chown -R scraper:scraper /opt/job_scraper &&
  sudo chmod +x /opt/job_scraper/run_shard.sh'

rsync -av smoke_test_input.xlsx azureuser@<vm-ip>:/tmp/
ssh azureuser@<vm-ip> 'sudo mv /tmp/smoke_test_input.xlsx /opt/job_scraper/data/ &&
                       sudo chown scraper:scraper /opt/job_scraper/data/*.xlsx'
```

---

## 4. Verify

```bash
sudo -u scraper bash -lc '
  set -a; . /opt/job_scraper/.env.scraper; set +a
  cd /opt/job_scraper
  .venv/bin/python test_job_scraper_offline.py   # 31 tests, no network
  .venv/bin/python preflight.py                  # deps, camoufox, DNS, live render
'
```

`preflight.py` exits non-zero if anything is broken and names it. It checks the
interpreter and venv, every required and optional package, the Camoufox package
*and* its downloaded browser binary, Xvfb, the resolved config paths, RAM/disk/fd
headroom against your worker counts, DNS and HTTPS reachability, the live
search-engine chain, and one real Camoufox page render.

---

## 5. Run

```bash
# Smoke test (100 companies)
sudo -u scraper bash -lc '
  set -a; . /opt/job_scraper/.env.scraper; set +a
  cd /opt/job_scraper && .venv/bin/python run_smoke_test.py --limit 100'

# Full job, sharded across 6 VMs — set SHARD_INDEX per VM (0..5)
sudo -u scraper bash -lc '
  cd /opt/job_scraper &&
  SHARD_INDEX=0 SHARD_COUNT=6 INPUT=/opt/job_scraper/data/full.xlsx ./run_shard.sh'
```

As a managed service (survives reboots, auto-restarts, resumes):

```bash
sudo cp job-scraper.service /etc/systemd/system/
# put SHARD_INDEX / SHARD_COUNT in /opt/job_scraper/.env.scraper per VM
sudo systemctl daemon-reload && sudo systemctl enable --now job-scraper
journalctl -u job-scraper -f
```

Collect the shards afterwards:

```bash
for i in 0 1 2 3 4 5; do
  scp azureuser@vm$i:/opt/job_scraper/output/shard_${i}_of_6.csv ./
done
python - <<'PY'
import glob, pandas as pd
frames = [pd.read_csv(f, encoding='utf-8-sig', low_memory=False)
          for f in sorted(glob.glob('shard_*_of_6.csv'))]
merged = pd.concat(frames, ignore_index=True)
merged.to_csv('merged_all.csv', index=False, encoding='utf-8-sig')
print(len(merged), 'rows;', merged['num_positions'].astype(float).sum(), 'positions')
PY
```

---

## 6. Tuning knobs (all env vars, no code edits)

Set these in `/opt/job_scraper/.env.scraper`:

| Variable | Default | Notes |
|---|---|---|
| `JOB_SCRAPER_BASE_DIR` | repo parent | root for cache/log/state |
| `JOB_SCRAPER_INPUT` / `_OUTPUT` / `_LOG` | under BASE_DIR | absolute paths |
| `JOB_SCRAPER_WORKERS` | 10 | HTTP worker threads |
| `JOB_SCRAPER_BROWSER_WORKERS` | 2 | Camoufox instances; the RAM driver |
| `CAMOUFOX_HEADLESS` | `true` | `virtual` = real Firefox in Xvfb, much harder to fingerprint, ~20% slower |
| `CAMOUFOX_HUMANIZE` | `true` | human-like cursor movement |
| `CAMOUFOX_GEOIP` | `false` | set `true` when using geo-located proxies |
| `CAMOUFOX_PROXY` | unset | `http://user:pass@host:port` |
| `CAMOUFOX_OS` | unset | e.g. `windows,macos` to vary the fingerprint |
| `CAMOUFOX_NODE_MODULES` | auto | only for the legacy `camoufox_js` fallback |

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `no usable Camoufox binding` | `pip install "camoufox[geoip]"` then `python -m camoufox fetch` |
| Render returns `None`, log says worker failed | Missing Firefox lib. `ldd ~/.cache/camoufox/camoufox \| grep 'not found'`, then apt-install it |
| `CAMOUFOX_HEADLESS=virtual` fails | `apt-get install xvfb` and `pip install pyvirtualdisplay` |
| Everything `Unreachable` | Check `preflight.py` DNS section; confirm the NSG allows outbound 443 |
| DNS failures under load | Confirm `resolvectl statistics` shows a growing cache; check `/etc/systemd/resolved.conf.d/10-job-scraper.conf` |
| Search engines all benched | Datacentre IPs get blocked. Set `CAMOUFOX_PROXY` to residential proxies; check `engine_status()` in the run summary |
| OOM kills | Lower `JOB_SCRAPER_BROWSER_WORKERS`; confirm the swapfile is active (`swapon --show`) |
| Run stalls near the end | One pathological site. Ceilings in `config.py` (`MAX_PAGINATION_PAGES`, `MAX_JOB_DETAIL_PAGES`) bound it; lower them if needed |
