# Implementation Plan - JunEdu Plugin Architecture & Dynamic UI Integration

This document outlines the design and step-by-step technical implementation plan for adding a lightweight, dynamic Plugin System to JunEdu according to [requirement.md](file:///d:/my-project/workspace-anki/jun-edu/requirement.md).

## Problem & Objectives

- **Goal**: Keep the JunEdu core application lightweight and decoupled from optional heavy features (such as OCR via PaddleOCR and AI Agent via local LLMs/Torch).
- **Dynamic UI**: Plugins register their own toolbar buttons, menu entries, context menu items, and stack pages. If a plugin is missing or disabled, its UI contributions must not appear in JunEdu.
- **Out-of-Process Workers**: Heavy ML packages (PaddleOCR, PyTorch, etc.) are executed in external worker executables (`ocr-worker.exe`, `agent-worker.exe`) communicating over standard line-delimited JSON IPC (`stdin`/`stdout`).
- **Isolation & Robustness**: Plugin failures, missing files, or crashes must be gracefully isolated so JunEdu core starts and runs without interruption.

---

## User Review Required

> [!IMPORTANT]
> **Dependency & Environment Isolation**:
> Optional dependencies like `paddleocr`, `paddle`, `torch` must be completely removed from the main application's environment imports and `JunEdu.spec` bundle requirements. Heavy workers will run as separate executables communicating via JSON-lines IPC.

> [!NOTE]
> **Dynamic Navigation**:
> Main toolbar buttons / navigation actions registered by plugins will dynamically add tabs/pages to `MainWindow`'s `QStackedWidget` without hardcoding any plugin checks inside `main_window.py`.

---

## Proposed Changes

### 1. Core Plugin Infrastructure (`src/core/plugins/`)

#### [NEW] [plugin_manifest.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/plugin_manifest.py)
- Data model (`PluginManifest`) for parsing `plugin.json`.
- Validates required fields (`id`, `name`, `version`, `api_version`, `entry`, `enabled`, `execution`).
- Ensures valid plugin ID formatting and security checks against directory traversal (`../`).

#### [NEW] [plugin_base.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/plugin_base.py)
- Defines abstract base class `JunEduPlugin`:
  - `plugin_id: str`
  - `initialize(context: PluginContext) -> None`
  - `shutdown() -> None`
- Defines plugin factory contract (`create_plugin() -> JunEduPlugin`).

#### [NEW] [plugin_context.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/plugin_context.py)
- `PluginContext` provided to plugins during initialization:
  - `ui: UIRegistry`
  - `logger: logging.Logger`
  - `workers: WorkerManager`
  - `get_resource_path(relative_path: str) -> str`

#### [NEW] [ui_registry.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/ui_registry.py)
- `UIRegistry` manages dynamic UI contributions:
  - `register_action(plugin_id, action_id, title, location, callback, icon=None)`
  - `register_page(plugin_id, page_id, title, widget_factory)`
  - `unregister_plugin(plugin_id)` for lifecycle cleanup.
- Signals and slots for attaching actions/pages to PySide6 widgets in `MainWindow`.

#### [NEW] [plugin_worker.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/plugin_worker.py) & [worker_manager.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/worker_manager.py)
- `PluginWorker`: Manages subprocess execution (`subprocess.Popen`) for external worker executables (`in_process` vs `process`).
- JSON-lines IPC protocol implementation (`send_request`, response parsing, non-blocking asynchronous I/O via Qt background threads).
- `WorkerManager`: Factory and lifecycle manager for lazy worker startup and graceful termination on application exit.

#### [NEW] [exceptions.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/exceptions.py)
- Custom exceptions: `PluginError`, `PluginManifestError`, `PluginIncompatibleError`, `WorkerError`.

#### [NEW] [plugin_manager.py](file:///d:/my-project/workspace-anki/jun-edu/src/core/plugins/plugin_manager.py)
- Main entry point for plugin discovery, loading, lifecycle, and error isolation:
  - Scans `plugins/` directory.
  - Loads and validates manifests (`plugin.json`).
  - Checks API compatibility (`PLUGIN_API_VERSION = "1"`).
  - Instantiates plugins safely in isolated `try...except` blocks.
  - Handles plugin cleanup on shutdown.

---

### 2. Main Application & UI Integration

#### [MODIFY] [main_window.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/main_window.py)
- Instantiate `UIRegistry` and `PluginManager`.
- Connect `UIRegistry` signals to dynamically populate menu bar, toolbar, and `stacked_widget`.
- Call `PluginManager.discover_and_load(context)` during startup sequence.

#### [MODIFY] [main.py](file:///d:/my-project/workspace-anki/jun-edu/main.py)
- Wire `PluginManager.shutdown()` during application cleanup (`QApplication.aboutToQuit`).

#### [MODIFY] [JunEdu.spec](file:///d:/my-project/workspace-anki/jun-edu/JunEdu.spec)
- Exclude heavy dependencies (`paddle`, `paddleocr`, `torch`, `torchvision`, etc.) from core PyInstaller build.

---

### 3. Example Plugins (`plugins/`)

#### [NEW] [plugins/ocr/plugin.json](file:///d:/my-project/workspace-anki/jun-edu/plugins/ocr/plugin.json) & [plugins/ocr/plugin.py](file:///d:/my-project/workspace-anki/jun-edu/plugins/ocr/plugin.py)
- OCR plugin implementation registering an OCR toolbar action / page.
- Uses lazy worker startup for `ocr-worker.exe`.

#### [NEW] [plugins/agent/plugin.json](file:///d:/my-project/workspace-anki/jun-edu/plugins/agent/plugin.json) & [plugins/agent/plugin.py](file:///d:/my-project/workspace-anki/jun-edu/plugins/agent/plugin.py)
- Agent plugin implementation registering Agent action/page.

---

## Verification Plan

### Automated Tests
- `pytest` or `unittest` suite testing:
  - Manifest parsing and validation rules.
  - API version compatibility checking.
  - Discovery of plugins in temporary test directories.
  - IPC JSON line encoder/decoder logic and error handling.
  - `UIRegistry` action and page registration and cleanup.

### Manual Verification
1. **No Plugins Case**: Launch app with an empty `plugins/` directory -> verifies core UI opens without errors or placeholder buttons.
2. **OCR Plugin Present Case**: Place `plugins/ocr` manifest & code -> launch app -> verify OCR menu/toolbar entry appears.
3. **Lazy Worker Test**: Verify `ocr-worker.exe` is not running on launch, but starts when OCR functionality is first triggered.
4. **Error Isolation Test**: Introduce a syntax error in `plugins/ocr/plugin.py` -> verify JunEdu logs error and starts cleanly without crashing.
