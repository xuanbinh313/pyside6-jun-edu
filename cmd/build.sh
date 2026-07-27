#!/bin/bash
set -euo pipefail

if command -v powershell.exe >/dev/null 2>&1; then
    running_ids="$(powershell.exe -NoProfile -Command "Get-Process JunEdu -ErrorAction SilentlyContinue | Where-Object { \$_.Path -like '*\\dist\\JunEdu.exe' } | ForEach-Object { \$_.Id }" | tr -d '\r' | xargs || true)"
    if [ -n "$running_ids" ]; then
        echo "Close dist/JunEdu.exe before building. Running process id(s): $running_ids" >&2
        exit 1
    fi
fi

backup_db=""
if [ -f ./dist/exams.db ]; then
    backup_db="./backup.db"
    mv ./dist/exams.db "$backup_db"
fi

.venv/Scripts/python.exe cmd/generate_config.py --env .env --out src/config.py
.venv/Scripts/python.exe cmd/check_plugin_dependencies.py
.venv/Scripts/python.exe cmd/build_plugin_workers.py --clean

rm -rf build dist

.venv/Scripts/pyinstaller --clean JunEdu.spec

.venv/Scripts/python.exe cmd/prepare_plugins.py --src plugins --out dist/plugins --clean

if [ -n "$backup_db" ]; then
    mv "$backup_db" ./dist/exams.db
fi
