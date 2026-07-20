$ErrorActionPreference = "Stop"

$backupDb = $null
if (Test-Path -LiteralPath ".\dist\exams.db") {
    $backupDb = ".\backup.db"
    Move-Item -LiteralPath ".\dist\exams.db" -Destination $backupDb -Force
}

.\.venv\Scripts\python.exe cmd\generate_config.py --env .env --out src\config.py

Remove-Item -LiteralPath ".\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath ".\dist" -Recurse -Force -ErrorAction SilentlyContinue

.\.venv\Scripts\pyinstaller.exe --clean JunEdu.spec

if ($null -ne $backupDb) {
    Move-Item -LiteralPath $backupDb -Destination ".\dist\exams.db" -Force
}
