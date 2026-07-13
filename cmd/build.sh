#!/bin/bash

mv ./dist/exams.db ./backup.db

rm -rf build dist

.venv/Scripts/pyinstaller --clean JunEdu.spec

mv ./backup.db ./dist/exams.db