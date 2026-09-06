#!/usr/bin/env bash
# A user installation: no sudo pip and no dependency on the checkout afterward.
set -euo pipefail
source_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${PYTHON:-python3}" "$source_dir/scripts/install_linux.py" "$@"
