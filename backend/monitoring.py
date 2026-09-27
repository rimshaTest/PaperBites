"""
Crash/error monitoring via Sentry - optional, same "no key, no-op" pattern as every other API
key in config.py. Without PAPERBITES_SENTRY_DSN set, init_monitoring() does nothing and the app
runs exactly as it did before this existed; errors just go to stdout/stderr like always.
"""
import logging

from config import Config

logger = logging.getLogger("paperbites.monitoring")


def init_monitoring() -> None:
    """Call once, at process startup, before the Starlette app is built."""
    dsn = Config().get("api.sentry_dsn")
    if not dsn:
        logger.info("PAPERBITES_SENTRY_DSN not configured - crash reporting disabled")
        return

    import sentry_sdk
    from sentry_sdk.integrations.starlette import StarletteIntegration
    from sentry_sdk.integrations.asgi import AsgiIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[StarletteIntegration(), AsgiIntegration()],
        traces_sample_rate=0.1,
    )
    logger.info("Sentry crash reporting enabled")
