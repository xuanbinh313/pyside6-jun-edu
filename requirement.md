Below is a requirement specification you can give to an AI agent.

---

# Requirement: Attach Environment Variables During One-File Build (No Runtime `.env`)

## Objective

Refactor the application so it no longer depends on an external `.env` file at runtime.

All required environment variables must be attached to the application before the
PyInstaller one-file build runs, allowing the generated executable to run
without requiring a separate `.env` file beside it.

The `.env` file may be used as a local build input only. It must not be loaded,
searched for, bundled as PyInstaller data, or required after the executable is
built.

---

## Requirements

### 1. Remove Runtime Dependency on `.env`

* The application must not require a `.env` file when running.
* Remove all calls to:

  * `load_dotenv()`
  * `find_dotenv()`
  * Any logic that searches for a `.env` file.

---

### 2. Create a Centralized Configuration Module

Create a new module (for example `config.py`) responsible for all application configuration.

Example:

```python
import os

os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "your-anon-key"

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
```

All configuration values should be exposed through constants instead of calling `os.getenv()` throughout the project.

Recommended build flow:

1. Keep local secrets in `.env` for development/build machines only.
2. Generate or update the centralized configuration module from `.env` before
   running PyInstaller.
3. Build the one-file executable with `JunEdu.spec`.
4. Run the executable without copying `.env` into `dist/`.

Example generated module:

```python
import os

SUPABASE_URL = "https://example.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
TTS_AGENT_URL = "https://api.jun-edu.xyz"

os.environ.setdefault("SUPABASE_URL", SUPABASE_URL)
os.environ.setdefault("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY)
os.environ.setdefault("TTS_AGENT_URL", TTS_AGENT_URL)
```

This module is included automatically in the PyInstaller one-file executable
because it is imported by the application. Do not add `.env` to `datas` in
`JunEdu.spec`.

---

### 3. Replace All `os.getenv()` Calls

Search the entire project for:

```python
os.getenv(...)
```

Replace them with imports from the centralized configuration module.

Example:

Before:

```python
url = os.getenv("SUPABASE_URL")
```

After:

```python
from config import SUPABASE_URL

url = SUPABASE_URL
```

---

### 4. Single Source of Truth

All application configuration must exist in exactly one place.

No hardcoded configuration values should exist elsewhere in the project.

---

## One-File Build Requirement

The build command should attach environment values by generating the
centralized configuration module before invoking PyInstaller:

```powershell
.\.venv\Scripts\python.exe cmd\generate_config.py --env .env --out src\config.py
.\.venv\Scripts\pyinstaller.exe --clean JunEdu.spec
```

The resulting executable must satisfy these checks:

* `dist/JunEdu.exe` starts when `.env` is absent.
* `dist/` does not need a copied `.env` file.
* The executable reads config constants from the centralized module.
* Error messages must not say a value is missing from `.env`; they should say
  the application configuration value is missing.

Because these values are embedded into the executable, treat the one-file build
artifact as containing the same secrets as the original `.env`.

---
