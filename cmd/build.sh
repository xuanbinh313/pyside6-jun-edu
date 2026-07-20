#!/bin/bash
set -euo pipefail

backup_db=""
if [ -f ./dist/exams.db ]; then
    backup_db="./backup.db"
    mv ./dist/exams.db "$backup_db"
fi

.venv/Scripts/python.exe cmd/generate_config.py --env .env --out src/config.py

rm -rf build dist

.venv/Scripts/pyinstaller --clean JunEdu.spec

if [ -n "$backup_db" ]; then
    mv "$backup_db" ./dist/exams.db
fi
