"""Re-export RedactSecretsFilter from flux_core to avoid core→bot import cycle.

The canonical implementation lives in flux_core.logging_filters so
flux_core.logging.configure_logging() can attach it without importing
flux_bot.
"""
from flux_core.logging_filters import RedactSecretsFilter

__all__ = ["RedactSecretsFilter"]
