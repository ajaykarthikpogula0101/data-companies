# Real run — 405,210 companies across 5 VMs

Not a smoke test. Each VM takes 81,042 companies and writes its own CSV; the five
CSVs merge into one file at the end.

Key: `C:\Users\Ajay karthik pogula\Downloads\vm1-50000_key.pem`
VM 1 (already created): `20.219.9.66` → shard **0**

| VM | shard | rows | rows with a website | output file |
|---|---|---|---|---|
| 1 — 20.219.9.66 | `-ShardIndex 0` | 81,042 | 34,124 | `<vm-hostname>_shard_0_of_5.csv` |
| 2 | `-ShardIndex 1` | 81,042 | 34,114 | `<vm-hostname>_shard_1_of_5.csv` |
| 3 | `-ShardIndex 2` | 81,042 | 34,111 | `<vm-hostname>_shard_2_of_5.csv` |
| 4 | `-ShardIndex 3` | 81,042 | 34,098 | `<vm-hostname>_shard_3_of_5.csv` |
| 5 | `-ShardIndex 4` | 81,042 | 34,078 | `<vm-hostname>_shard_4_of_5.csv` |

Each output file is named after the machine that produced it (the VM's own
hostname, e.g. `scraper-vm-2_shard_1_of_5.csv`), so the five files never collide
when they end up in one folder and you can always tell which VM made which rows.
Override with `-VmName` if you want a different label.

Splitting is **interleaved** — each VM takes every 5th row — so all five get the
same amount of real work. Contiguous blocks would not: the input is grouped by
source, and block 3 has only 28,352 rows with a website against block 1's 36,622,
a 29% imbalance that would leave the whole run waiting on one machine for an
extra day. Verified: every one of the 405,210 rows lands in exactly one shard,
and no row lands in two.

At ~10 companies/min per VM, 81,042 rows is ~5.6 days. More workers on a bigger
SKU shortens that; `vm_status.ps1` prints each VM's measured rate and its own ETA
once it is running.

---

## Step 0 — create the other 4 VMs with the same key

You only have VM 1. Derive the public key from the .pem you already have so all
five VMs accept the same key:

```powershell
cd D:\data_companies
$KEY = "C:\Users\Ajay karthik pogula\Downloads\vm1-50000_key.pem"
ssh-keygen -y -f "$KEY" | Out-File -Encoding ascii .\vm_key.pub
```

```powershell
$RG  = "company-super-scraper"
$PUB = (Get-Content .\vm_key.pub -Raw).Trim()

foreach ($i in 2,3,4,5) {
  az vm create `
    --resource-group $RG --name "scraper-vm-$i" `
    --image Ubuntu2404 --size Standard_D4as_v5 `
    --admin-username azureuser `
    --ssh-key-values "$PUB" `
    --os-disk-size-gb 128 --public-ip-sku Standard
}

az vm list-ip-addresses -g $RG -o table    # collect the 4 new public IPs
```

Pass the key **content**, not `@vm_key.pub` — in PowerShell a bare `@name` is the
splatting operator and the argument would be swallowed.

Do not use B-series (burstable) sizes — CPU credits run out under sustained
scraping and everything silently slows down. `Standard_D4as_v5` (4 vCPU / 16 GB)
is the sweet spot; the setup script sizes the worker counts from whatever it
finds.

---

## Step 1 — set up VM 1 and start it

One command per VM. It is idempotent — if anything fails, fix it and re-run.

```powershell
cd D:\data_companies
.\deploy\setup_vm.ps1 -Ip 20.219.9.66 -ShardIndex 0 -Start
```

What it does, in order, printing each step:

1. locks down the .pem permissions (`icacls`) — OpenSSH refuses a loose key
2. SSHes in and reads vCPU / RAM / free disk, then sizes
   `JOB_SCRAPER_WORKERS` and `JOB_SCRAPER_BROWSER_WORKERS` from them
3. runs `azure_ubuntu_setup.sh` — apt packages, Firefox runtime libs, Xvfb,
   Python venv, `camoufox[geoip]` + browser download, systemd-resolved DNS cache
   with 1.1.1.1 / 8.8.8.8 / 9.9.9.9 fallback, 4 GB swap, `scraper` user
   (5–10 minutes)
4. copies the code — `job_scraper/*.py`, the runners, the tests, `deploy/` —
   and never `node_modules` (it holds the Windows-only `impit-win32-x64-msvc`
   binary), `.venv`, or `.browser_cache`
5. copies `data_7.7m_405k.csv` (37 MB; skipped if already there at the same size)
6. writes `/opt/job_scraper/.env.scraper` with this VM's shard index, paths and
   worker counts
7. runs the verification: the offline test suite, the bad-website suite, then
   `preflight.py` — which does a **live Camoufox render** and a live Greenhouse
   API call. This is a correctness gate, not a pilot run; it takes about a
   minute. If it fails, the run does not start.
8. with `-Start`: installs the systemd service and begins the real run

Skip individual stages when re-running: `-SkipBootstrap`, `-SkipCode`,
`-SkipData`, `-SkipTests`.

---

## Step 2 — the other four

Same command, new IP, next shard index:

```powershell
.\deploy\setup_vm.ps1 -Ip <vm2-ip> -ShardIndex 1 -Start
.\deploy\setup_vm.ps1 -Ip <vm3-ip> -ShardIndex 2 -Start
.\deploy\setup_vm.ps1 -Ip <vm4-ip> -ShardIndex 3 -Start
.\deploy\setup_vm.ps1 -Ip <vm5-ip> -ShardIndex 4 -Start
```

Start them 10–15 minutes apart. All five hit the same search engines from the
same Azure region, and simultaneous cold starts are the one thing likely to get
the whole region rate-limited at once.

Getting a shard index wrong is not destructive — two VMs on the same index just
do the same work twice and one shard never gets done. `vm_status.ps1` shows each
VM's index, so check it after starting.

---

## You can shut the laptop down

The run lives on the VMs, not on your laptop. Once `setup_vm.ps1 ... -Start`
finishes, the work is a systemd service on the VM: it keeps going when you close
PowerShell, when you disconnect, and when your laptop is off. It also restarts
itself if it crashes, and starts again automatically if the VM reboots.

Two things to check before you walk away:

```powershell
# 1. the service is actually running on each VM
ssh -i "$KEY" azureuser@20.219.9.66 'systemctl is-active job-scraper'   # -> active

# 2. no auto-shutdown schedule on the VMs (Azure adds one on some subscriptions)
az vm auto-shutdown show -g company-super-scraper -n scraper-vm-1 2>$null
```

If auto-shutdown is set, turn it off, or the VM will stop overnight:

```powershell
az vm auto-shutdown -g company-super-scraper -n scraper-vm-1 --off
```

Come back in two days and go to Step 4 to download the files. If a VM did stop
for any reason, starting it again resumes from where it left off — no work is
lost or repeated:

```powershell
az vm start -g company-super-scraper -n scraper-vm-1
ssh -i "$KEY" azureuser@20.219.9.66 'sudo systemctl start job-scraper'
```

---

## Step 3 — watch it

```powershell
.\deploy\vm_status.ps1 -Ips 20.219.9.66,<ip2>,<ip3>,<ip4>,<ip5> -Watch
```

```
VM                shard        rows     pct state       comp/min ffx     disk eta
20.219.9.66       0/5         12480   15.4% active          10.4 4        102G  4.6d
...
TOTAL                         61903   15.3%
```

`ffx` is the live Camoufox process count — if it sits at 0 on a VM whose row
count is still climbing, that VM is only doing plain HTTP and something is wrong
with the browser. Per-VM detail:

```powershell
ssh -i "$KEY" azureuser@20.219.9.66 'journalctl -u job-scraper -n 50 --no-pager'
ssh -i "$KEY" azureuser@20.219.9.66 'tail -f /opt/job_scraper/logs/scraper.log'
```

Stop / resume any VM at any time — resume is on by default, so it picks up from
where it stopped and never re-does or duplicates a company:

```powershell
ssh -i "$KEY" azureuser@20.219.9.66 'sudo systemctl stop job-scraper'
ssh -i "$KEY" azureuser@20.219.9.66 'sudo systemctl start job-scraper'
```

---

## Step 4 — collect and merge

Safe to run any time for a partial result; run it again at the end for the final
file.

```powershell
.\deploy\collect_shards.ps1 -Ips 20.219.9.66,<ip2>,<ip3>,<ip4>,<ip5> -Merge
```

It asks each VM what its output file is called, downloads it into `.\shards\`
keeping the VM's name in the filename, and then streams all five into
`merged_all.csv` — dropping any duplicate company key and printing per-file row
counts plus the total position count. The per-VM files stay in `.\shards\`, so
you keep both the merged file and the five originals.

---

## Companies with no website

234,685 of the 405,210 rows have no WEBSITE value, and more have one that is
dead or points somewhere else. The scraper does not depend on that column. For
those rows it:

1. guesses domains from the company name and its country — "Acme Foods Ltd" in
   Germany becomes acmefoods.de, acme-foods.de, acmefoods.com and so on — and
   checks DNS before fetching anything, so a wrong guess costs nothing;
2. accepts a guess only if the page really is that company (60% of the name's
   distinctive words must appear on it), so no one else's jobs get attached;
3. searches for the official website by name;
4. searches for an ATS board published under the company name, asking the
   vendors that country actually uses first (Gupy and Solides for Brazil,
   softgarden / d.vinci / Keka / Darwinbox for Germany and India);
5. searches for job pages by name and verifies each one before extracting.

These rows are search-driven, so they get a bigger query budget than a company
whose own site answered: `JOB_SCRAPER_SEARCH_BUDGET_NO_SITE` (10) instead of
`JOB_SCRAPER_SEARCH_BUDGET` (5). A company with a working website still costs
**zero** search queries.

That is a lot more searching across 234,685 companies. If the run summary shows
engines getting benched, lower `JOB_SCRAPER_SEARCH_BUDGET_NO_SITE` to 6 or 7 in
`.env.scraper` and restart — nothing else needs to change.

| Setting | Default | What it controls |
|---|---|---|
| `JOB_SCRAPER_SEARCH_BUDGET` | 5 | queries for a company with a working site |
| `JOB_SCRAPER_SEARCH_BUDGET_NO_SITE` | 10 | queries once no usable site is found |
| `JOB_SCRAPER_ATS_BOARD_GROUPS` | 1 | vendor groups asked about normally |
| `JOB_SCRAPER_ATS_BOARD_GROUPS_NO_SITE` | 3 | vendor groups asked about with no site |
| `JOB_SCRAPER_DOMAIN_GUESSES` | 6 | domains guessed per company |
| `JOB_SCRAPER_DOMAIN_GUESS_EVIDENCE` | 0.60 | how much of the name must appear before a guess is accepted |

---

## If something goes wrong

| Symptom | What to do |
|---|---|
| `preflight.py` fails on the Camoufox render | `ssh` in, then `sudo -u scraper /opt/job_scraper/.venv/bin/python -m camoufox fetch`; check `ldd ~scraper/.cache/camoufox/camoufox \| grep 'not found'` |
| Everything comes back `Unreachable` | DNS or egress. `resolvectl statistics` should show a growing cache; confirm the NSG allows outbound 443 |
| Several search engines benched in the run summary | Datacentre IPs get blocked. Lower `JOB_SCRAPER_SEARCH_BUDGET` (default 5) in `.env.scraper`, or set `CAMOUFOX_PROXY` to residential proxies, and stagger restarts |
| A VM gets OOM-killed | Lower `JOB_SCRAPER_BROWSER_WORKERS` — each is a full Firefox at ~700 MB — then `sudo systemctl restart job-scraper` |
| Row count stops climbing on one VM | `journalctl -u job-scraper -n 100`. A single pathological site is bounded by `COMPANY_TIME_BUDGET=180`, so a real stall means the process died; the service restarts it after 60s |
| Disk filling up | `.browser_cache` self-prunes at 5 GB, output CSVs grow ~1 KB/row. `du -sh /opt/job_scraper/*` to see which |
