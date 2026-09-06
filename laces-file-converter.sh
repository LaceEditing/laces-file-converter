#!/usr/bin/env bash
set -euo pipefail
source_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$source_dir/main.py" ]]; then
    if [[ -x "$source_dir/.venv/bin/python" ]]; then
        exec "$source_dir/.venv/bin/python" "$source_dir/main.py" "$@"
    fi
    exec python3 "$source_dir/main.py" "$@"
fi
# Flatpak installs this launcher in /app/bin.
exec python3 /app/share/laces-file-converter/main.py "$@"
