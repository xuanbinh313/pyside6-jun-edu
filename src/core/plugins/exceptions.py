"""Plugin system exception types."""


class PluginError(Exception):
    """Base class for plugin system failures."""


class PluginManifestError(PluginError):
    """Raised when a plugin manifest is missing or invalid."""


class PluginIncompatibleError(PluginError):
    """Raised when a plugin targets an unsupported API version."""


class WorkerError(PluginError):
    """Raised when an out-of-process plugin worker fails."""
