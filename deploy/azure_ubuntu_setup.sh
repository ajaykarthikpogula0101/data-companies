#!/usr/bin/env bash
#
# Bootstrap an Azure Ubuntu 22.04 / 24.04 VM to run job_scraper with Camoufox.
#
# Idempotent: safe to re-run. Every step checks before it acts.
#
#   sudo bash azure_ubuntu_setup.sh                    # full setup
#   sudo bash azure_ubuntu_setup.sh --with-node        # also install Node 22
#   sudo bash azure_ubuntu_setup.sh --skip-browser     # skip the ~250MB fetch
#
set -Eeuo pipefail

APP_USER="${APP_USER:-scraper}"
APP_DIR="${APP_DIR:-/opt/job_scraper}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
WITH_NODE=0
SKIP_BROWSER=0

for arg in "$@"; do
  case "$arg" in
    --with-node) WITH_NODE=1 ;;
    --skip-browser) SKIP_BROWSER=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  echo "run with sudo" >&2; exit 1
fi

. /etc/os-release
log "Ubuntu ${VERSION_ID:-unknown} on $(uname -m)"

# ---------------------------------------------------------------------------
# 1. Base OS packages
# ---------------------------------------------------------------------------
log "Installing base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
  ca-certificates curl wget gnupg git unzip xz-utils \
  build-essential pkg-config \
  python3 python3-venv python3-dev python3-pip \
  xvfb x11-utils \
  fonts-liberation fonts-dejavu-core fontconfig \
  tzdata locales jq

# ---------------------------------------------------------------------------
# 2. Firefox runtime libraries (Camoufox is a patched Firefox).
#    Package names moved between 22.04 and 24.04, so install best-effort and
#    report anything genuinely missing rather than aborting the whole run.
# ---------------------------------------------------------------------------
log "Installing Firefox/Camoufox runtime libraries"
LIBS=(
  libgtk-3-0 libgdk-pixbuf-2.0-0 libglib2.0-0
  libx11-6 libx11-xcb1 libxcb1 libxcb-shm0 libxcomposite1 libxcursor1
  libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxtst6 libxt6
  libdbus-1-3 libdbus-glib-1-2
  libnss3 libnspr4
  libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0
  libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libfreetype6 libfontconfig1
  libegl1 libgl1 libgbm1 libdrm2 libgles2
  libcups2 libpci3 libudev1 libexpat1 libxkbcommon0
  libvpx-dev libevent-dev libopus0 libwebp-dev
)
# alsa + a couple of others differ by release
for pkg in libasound2t64 libasound2; do
  apt-cache show "$pkg" >/dev/null 2>&1 && { LIBS+=("$pkg"); break; }
done
for pkg in libjpeg-turbo8 libjpeg62-turbo libjpeg8; do
  apt-cache show "$pkg" >/dev/null 2>&1 && { LIBS+=("$pkg"); break; }
done
for pkg in libcups2t64; do
  apt-cache show "$pkg" >/dev/null 2>&1 && LIBS+=("$pkg")
done

MISSING=()
for pkg in "${LIBS[@]}"; do
  if apt-cache show "$pkg" >/dev/null 2>&1; then
    apt-get install -y --no-install-recommends "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
  fi
done
[[ ${#MISSING[@]} -gt 0 ]] && warn "could not install: ${MISSING[*]} (usually harmless)"

# ---------------------------------------------------------------------------
# 3. DNS: cache locally and add public fallbacks.
#    Azure's platform resolver (168.63.129.16) rate-limits under a scraper's
#    query volume, which is exactly what produced NameResolutionError storms.
#    systemd-resolved caching + 1.1.1.1/8.8.8.8 fallback removes that ceiling.
# ---------------------------------------------------------------------------
log "Configuring DNS caching and fallback resolvers"
if systemctl list-unit-files | grep -q '^systemd-resolved\.service'; then
  mkdir -p /etc/systemd/resolved.conf.d
  cat > /etc/systemd/resolved.conf.d/10-job-scraper.conf <<'EOF'
[Resolve]
Cache=yes
CacheFromLocalhost=no
DNSStubListener=yes
FallbackDNS=1.1.1.1 8.8.8.8 9.9.9.9
DNSSEC=no
ReadEtcHosts=yes
EOF
  systemctl restart systemd-resolved || warn "systemd-resolved restart failed"
  resolvectl statistics 2>/dev/null | head -12 || true
else
  warn "systemd-resolved not present; relying on job_scraper/netcache.py only"
fi

# ---------------------------------------------------------------------------
# 4. Kernel / limits tuning for many concurrent sockets
# ---------------------------------------------------------------------------
log "Tuning file descriptors and network limits"
cat > /etc/security/limits.d/90-job-scraper.conf <<EOF
$APP_USER soft nofile 65535
$APP_USER hard nofile 65535
root      soft nofile 65535
root      hard nofile 65535
EOF
cat > /etc/sysctl.d/90-job-scraper.conf <<'EOF'
net.ipv4.ip_local_port_range = 15000 65000
net.ipv4.tcp_fin_timeout = 20
net.ipv4.tcp_tw_reuse = 1
net.core.somaxconn = 4096
fs.file-max = 200000
vm.swappiness = 10
EOF
sysctl --system >/dev/null

# Firefox is memory-hungry; a swapfile prevents OOM kills on 8GB SKUs.
if ! swapon --show | grep -q '/swapfile'; then
  log "Creating 4G swapfile"
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# ---------------------------------------------------------------------------
# 5. Application user and directory
# ---------------------------------------------------------------------------
log "Preparing $APP_DIR (user: $APP_USER)"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$APP_USER"
mkdir -p "$APP_DIR"/{data,output,logs}
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# ---------------------------------------------------------------------------
# 6. Python virtualenv + dependencies
# ---------------------------------------------------------------------------
log "Creating virtualenv and installing Python dependencies"
sudo -u "$APP_USER" python3 -m venv "$VENV_DIR" 2>/dev/null || true
PIP="$VENV_DIR/bin/pip"
sudo -u "$APP_USER" "$PIP" install --upgrade pip wheel setuptools -q

REQ="$APP_DIR/requirements.txt"
if [[ ! -f "$REQ" ]]; then
  warn "$REQ not found; writing a default one"
  cat > "$REQ" <<'EOF'
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.0
openpyxl>=3.1
pandas>=2.0
langdetect>=1.0.9
python-dotenv>=1.0
dnspython>=2.4
googlesearch-python>=1.2
camoufox[geoip]>=0.4
playwright>=1.45
pyvirtualdisplay>=3.0
EOF
  chown "$APP_USER":"$APP_USER" "$REQ"
fi
sudo -u "$APP_USER" "$PIP" install -q -r "$REQ"

# camoufox + the virtual-display helper must be present regardless of what the
# requirements file says, since browser_fetch.py imports camoufox.sync_api.
sudo -u "$APP_USER" "$PIP" install -q "camoufox[geoip]" pyvirtualdisplay dnspython

# ---------------------------------------------------------------------------
# 7. Fetch the Camoufox browser binary (~250MB)
# ---------------------------------------------------------------------------
if [[ $SKIP_BROWSER -eq 0 ]]; then
  log "Fetching the Camoufox browser build"
  sudo -u "$APP_USER" "$VENV_DIR/bin/python" -m camoufox fetch
else
  warn "--skip-browser: run '$VENV_DIR/bin/python -m camoufox fetch' before scraping"
fi

# ---------------------------------------------------------------------------
# 8. Optional: Node 22 (only if you also want camofox-browser's server.js)
# ---------------------------------------------------------------------------
if [[ $WITH_NODE -eq 1 ]]; then
  log "Installing Node.js 22"
  if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | sed 's/v\([0-9]*\).*/\1/')" -lt 22 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
  fi
  node -v
fi

# ---------------------------------------------------------------------------
# 9. Environment file
# ---------------------------------------------------------------------------
ENVFILE="$APP_DIR/.env.scraper"
if [[ ! -f "$ENVFILE" ]]; then
  log "Writing $ENVFILE"
  cat > "$ENVFILE" <<EOF
# --- paths -----------------------------------------------------------------
JOB_SCRAPER_BASE_DIR=$APP_DIR
JOB_SCRAPER_INPUT=$APP_DIR/data/smoke_test_input.xlsx
JOB_SCRAPER_OUTPUT=$APP_DIR/output/ajay.csv
JOB_SCRAPER_LOG=$APP_DIR/logs/scraper.log

# --- concurrency -----------------------------------------------------------
# HTTP worker threads. Start at 2x vCPU; watch memory before raising.
JOB_SCRAPER_WORKERS=10
# Camoufox instances. Each is a full Firefox: ~400-700MB resident.
JOB_SCRAPER_BROWSER_WORKERS=2

# --- camoufox --------------------------------------------------------------
# "virtual" runs a real Firefox inside Xvfb: slower, much harder to fingerprint.
# "true" is plain headless. "false" needs a real display.
CAMOUFOX_HEADLESS=virtual
CAMOUFOX_HUMANIZE=true
CAMOUFOX_GEOIP=false
# CAMOUFOX_PROXY=http://user:pass@proxy.example:8080
# CAMOUFOX_OS=windows,macos

PYTHONUNBUFFERED=1
EOF
  chown "$APP_USER":"$APP_USER" "$ENVFILE"
  chmod 600 "$ENVFILE"
fi

log "Done. Next steps:"
cat <<EOF

  1. Copy the code and input onto the VM:
       rsync -av --exclude '.venv' --exclude '.browser_cache' \\
             ./job_scraper ./run_smoke_test.py ./test_job_scraper_offline.py \\
             ./requirements.txt  $APP_USER@<vm-ip>:$APP_DIR/
       rsync -av smoke_test_input.xlsx $APP_USER@<vm-ip>:$APP_DIR/data/

  2. Verify the install:
       sudo -u $APP_USER bash -c 'set -a; . $ENVFILE; set +a; $VENV_DIR/bin/python $APP_DIR/preflight.py'

  3. Offline test suite (no network):
       sudo -u $APP_USER $VENV_DIR/bin/python $APP_DIR/test_job_scraper_offline.py

  4. Smoke test:
       sudo -u $APP_USER bash -c 'set -a; . $ENVFILE; set +a; $VENV_DIR/bin/python $APP_DIR/run_smoke_test.py --limit 100'

EOF
