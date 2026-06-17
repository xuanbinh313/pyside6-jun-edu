#!/bin/bash
# build pyinstaller onefile, noconsole, windows platform
# add data: assets;assets, views;views, *.ui;.
.venv/Scripts/pyinstaller --onefile \
  --noconsole \
  --windowed \
  --name="JunEdu" \
  --add-data "ui;ui" \
  --add-data "src;src" \
  --add-data "resources;resources" \
  main.py

