# ==============================================================================
# Dockerfile to Build and Run SAD (Strategic Accelerator Design) Software
# =============================================
# Author(s):  John P T Salvesen
# Email:      john.salvesen@cern.ch
# Date:       30-09-2025
# ==============================================================================

################################################################################
# User Parameters
################################################################################
ARG SAD_REPO_URL="https://github.com/KatsOide/SAD.git"
ARG SAD_BRANCH="master"
ARG SAD_SMOKE_PATH="tests/sad_installation_test.sad"

################################################################################
# 1: Build SAD from source
################################################################################
FROM ubuntu:24.04 AS builder

########################################
# Re-declare build args
########################################
ARG SAD_REPO_URL
ARG SAD_BRANCH
ARG SAD_SMOKE_PATH
ARG DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_FRONTEND=noninteractive

########################################
# Get X11 headers and groff
########################################
RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    git make gfortran build-essential ca-certificates pkg-config \
    libx11-dev groff; \
  (apt-get install -y --no-install-recommends libgfortran5 || \
   apt-get install -y --no-install-recommends libgfortran6 || true); \
  (apt-get install -y --no-install-recommends libquadmath0 || true); \
  rm -rf /var/lib/apt/lists/*

########################################
# Clone SAD source
########################################
# Requested branch, otherwise default branch
RUN set -eux; \
  if git ls-remote --exit-code --heads "${SAD_REPO_URL}" "${SAD_BRANCH}" >/dev/null 2>&1; then \
    git clone --depth 1 --branch "${SAD_BRANCH}" "${SAD_REPO_URL}" /opt/sad/src; \
  else \
    git clone --depth 1 "${SAD_REPO_URL}" /opt/sad/src; \
  fi
WORKDIR /opt/sad/src

########################################
# Patch first 70 lines of sad.conf (per KEK note)
########################################
# Original Makefile.unx and sad.conf files designed for legacy Unix
# KEK's installation instructions say:
#   "Use only the first 70 lines of sad.conf for building SAD locally."
RUN awk 'NR<=70' sad.conf > sad.conf.new && mv sad.conf.new sad.conf

########################################
# Build SAD and check
########################################
RUN make depend && make -s exe
RUN test -x /opt/sad/src/bin/gs

########################################
# Collect exact runtime libs
########################################
RUN set -eux; \
  ARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"; echo "$ARCH" > /opt/arch.txt; \
  mkdir -p /opt/rtlibs; \
  cp -a "/usr/lib/${ARCH}/libgfortran.so."* /opt/rtlibs/ || true; \
  cp -a "/usr/lib/${ARCH}/libquadmath.so."* /opt/rtlibs/ || true; \
  cp -a "/lib/${ARCH}/libgcc_s.so."*      /opt/rtlibs/ || true; \
  cp -a "/lib/${ARCH}/libm.so."*          /opt/rtlibs/ || true; \
  cp -a "/lib/${ARCH}/libc.so."*          /opt/rtlibs/ || true; \
  cp -a "/lib/${ARCH}/libpthread.so."*    /opt/rtlibs/ || true; \
  cp -a "/lib/${ARCH}/librt.so."*         /opt/rtlibs/ || true; \
  cp -a "/lib/${ARCH}/libdl.so."*         /opt/rtlibs/ || true

################################################################################
# 2: Runtime image with SAD + Python
################################################################################
FROM ubuntu:24.04 AS runtime
ARG DEBIAN_FRONTEND=noninteractive
ARG SAD_SMOKE_PATH

########################################
# Get runtime dependencies
########################################
RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-6 libc-bin curl ca-certificates bzip2 gcc \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/sad/src /opt/sad/src
COPY --from=builder /opt/rtlibs/ /usr/local/lib/
RUN ldconfig

########################################
# Copy environment.yml for micromamba
########################################
COPY environment.yml /tmp/environment.yml

########################################
# Copy build test into image
########################################
COPY ${SAD_SMOKE_PATH} /opt/smoke.sad

########################################
# Create environment with micromamba
########################################
SHELL ["/bin/bash", "-lc"]
ENV MAMBA_ROOT_PREFIX=/opt/micromamba
RUN set -eux; \
  # 1) ensure compiler exists for pip wheels (e.g., xdeps). Install temporarily.
  apt-get update; \
  apt-get install -y --no-install-recommends build-essential; \
  \
  # 2) fetch micromamba (arch-aware) and install to PATH
  ARCH="$(uname -m)"; \
  case "$ARCH" in x86_64) MM_ARCH="64" ;; aarch64) MM_ARCH="aarch64" ;; \
    *) echo "Unsupported arch for micromamba: $ARCH" && exit 1 ;; esac; \
  curl -fsSL "https://micro.mamba.pm/api/micromamba/linux-${MM_ARCH}/latest" -o /tmp/micromamba.tar.bz2; \
  tar -xjf /tmp/micromamba.tar.bz2 -C /usr/local/bin --strip-components=1 bin/micromamba; \
  chmod +x /usr/local/bin/micromamba; \
  micromamba --version; \
  \
  # 3) create env from environment.yml (required & non-empty)
  test -s /tmp/environment.yml || (echo "environment.yml is missing or empty" && exit 1); \
  micromamba create -y -n sad2xs -f /tmp/environment.yml; \
  echo 'source /opt/micromamba/etc/profile.d/micromamba.sh && micromamba activate sad2xs' > /etc/profile.d/zz-mamba-activate.sh; \
  \
  # 4) remove build tools to keep image lean
  apt-get purge -y --auto-remove build-essential; \
  rm -rf /var/lib/apt/lists/*

########################################
# SAD launcher script
########################################
RUN printf '%s\n' '#!/usr/bin/env bash' \
  'set -e' \
  'SAD_DIR="/opt/sad/src"' \
  'GS_EXEC="$SAD_DIR/bin/gs"' \
  'CALL_DIR="$(pwd)"' \
  'if [[ $# -gt 0 ]]; then' \
  '  if [[ "$1" = /* ]]; then SAD_INPUT="$1"; else SAD_INPUT="$(realpath "$CALL_DIR/$1")"; fi' \
  '  shift; cd "$CALL_DIR" || exit 1; exec "$GS_EXEC" "$SAD_INPUT" "$@"' \
  'else' \
  '  cd "$SAD_DIR" || exit 1; exec "$GS_EXEC"' \
  'fi' > /usr/local/bin/sad && chmod +x /usr/local/bin/sad

########################################
# Smoke helper test at startup
########################################
RUN printf '%s\n' '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  'FILE="${1:-/opt/smoke.sad}"' \
  'TO="${2:-10}"' \
  'if [[ ! -f "${FILE}" ]]; then echo "[sad-smoke] WARN: ${FILE} not found; using fallback"; FILE="/tmp/smoke.sad"; printf "end;\n" > "$FILE"; fi' \
  'echo "========== SAD Smoke Test =========="' \
  'echo "File: ${FILE}"' \
  'echo -n "Version: "; sad --help | head -n 1 || true' \
  'timeout "${TO}" sad "${FILE}" >/dev/null || { EC=$?; echo "[sad-smoke] FAIL (exit ${EC})"; exit ${EC}; }' \
  'echo "[sad-smoke] PASS"' \
  'echo "===================================="' \
  > /usr/local/bin/sad-smoke && chmod +x /usr/local/bin/sad-smoke

########################################
# Activate environment and run smoke test on start
########################################
ENV PATH="/opt/micromamba/envs/sad2xs/bin:/usr/local/bin:${PATH}" \
    MPLBACKEND=Agg \
    SAD_SMOKE_ON_START=/opt/smoke.sad \
    SAD_SMOKE_TIMEOUT=10

RUN printf '%s\n' '#!/usr/bin/env bash' \
  'set -e' \
  'if [ -f /opt/micromamba/etc/profile.d/micromamba.sh ] && [ -d /opt/micromamba/envs/sad2xs ]; then' \
  '  . /opt/micromamba/etc/profile.d/micromamba.sh' \
  '  micromamba activate sad2xs' \
  'fi' \
  'if [[ "${SKIP_SMOKE:-0}" != "1" ]]; then' \
  '  /usr/local/bin/sad-smoke "${SAD_SMOKE_ON_START}" "${SAD_SMOKE_TIMEOUT}"' \
  'fi' \
  'exec "$@"' > /usr/local/bin/with-mamba && chmod +x /usr/local/bin/with-mamba

ENTRYPOINT ["/usr/local/bin/with-mamba"]
CMD ["bash"]

WORKDIR /work
