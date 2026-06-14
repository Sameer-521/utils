#!/usr/bin/env bash
set -euo pipefail

REPO="Sameer-521/utils"
BRANCH="main"
INSTALL_DIR="${HOME}/.local/bin"
BINARY="${INSTALL_DIR}/crun"

echo "==> Downloading crun from github.com/${REPO} (${BRANCH})..."

mkdir -p "${INSTALL_DIR}"
curl -fsSL "https://raw.githubusercontent.com/${REPO}/refs/heads/${BRANCH}/crun/crun.py" -o "${BINARY}"
chmod +x "${BINARY}"

echo "==> Installed to ${BINARY}"

if ! echo "${PATH}" | tr ':' '\n' | grep -qxF "${INSTALL_DIR}"; then
    echo
    echo "NOTE: ${INSTALL_DIR} is not on your PATH."
    echo "Add this to your shell rc file:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo
echo "Run 'crun' to verify."
