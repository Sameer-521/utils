#!/usr/bin/env bash
set -euo pipefail

REPO="Sameer-521/utils"
BRANCH="main"
CRUN_HOME="${HOME}/.crun"
BIN_DIR="${HOME}/.local/bin"
SYMLINK="${BIN_DIR}/crun"

TMP_BASE="${TMPDIR:-}"
if [ -z "${TMP_BASE}" ] && [ -n "${PREFIX:-}" ] && [ -d "${PREFIX}/tmp" ]; then
  TMP_BASE="${PREFIX}/tmp"
fi
TMP_BASE="${TMP_BASE:-/tmp}"
mkdir -p "${TMP_BASE}"
TMPDIR=$(mktemp -d "${TMP_BASE}/crun-install.XXXXXX")

cleanup() { rm -rf "${TMPDIR}"; }
trap cleanup EXIT

echo "==> Downloading crun from github.com/${REPO} (${BRANCH})..."

git clone --depth 1 --branch "${BRANCH}" "https://github.com/${REPO}.git" "${TMPDIR}"

rm -rf "${CRUN_HOME}"
cp -r "${TMPDIR}/crun" "${CRUN_HOME}"
chmod +x "${CRUN_HOME}/__main__.py"

mkdir -p "${BIN_DIR}"
ln -sf "${CRUN_HOME}/__main__.py" "${SYMLINK}"

echo "==> Installed to ${SYMLINK}"

if ! echo "${PATH}" | tr ':' '\n' | grep -qxF "${BIN_DIR}"; then
  echo
  echo "NOTE: ${BIN_DIR} is not on your PATH."
  echo "Add this to your shell rc file:"
  echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo
echo "Run 'crun' to verify."
