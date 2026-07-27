$ErrorActionPreference = "Stop"

$runningDistApp = Get-Process JunEdu -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and (Resolve-Path -LiteralPath $_.Path).Path -eq (Resolve-Path -LiteralPath ".\dist\JunEdu.exe" -ErrorAction SilentlyContinue).Path
}
if ($runningDistApp) {
    $ids = ($runningDistApp | ForEach-Object { $_.Id }) -join ", "
    throw "Close dist\JunEdu.exe before building. Running process id(s): $ids"
}

$backupDb = $null
if (Test-Path -LiteralPath ".\dist\exams.db") {
    $backupDb = ".\backup.db"
    Move-Item -LiteralPath ".\dist\exams.db" -Destination $backupDb -Force
}

.\.venv\Scripts\python.exe cmd\generate_config.py --env .env --out src\config.py
.\.venv\Scripts\python.exe cmd\check_plugin_dependencies.py
.\.venv\Scripts\python.exe cmd\build_plugin_workers.py --clean

Remove-Item -LiteralPath ".\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath ".\dist" -Recurse -Force -ErrorAction SilentlyContinue

.\.venv\Scripts\pyinstaller.exe --clean JunEdu.spec

.\.venv\Scripts\python.exe cmd\prepare_plugins.py --src plugins --out dist\plugins --clean

if ($null -ne $backupDb) {
    Move-Item -LiteralPath $backupDb -Destination ".\dist\exams.db" -Force
}
