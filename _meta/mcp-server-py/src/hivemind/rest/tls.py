from __future__ import annotations

import logging
import ssl

logger = logging.getLogger(__name__)

_warnings_suppressed = False


def build_tls_verify(verify_setting: bool | str) -> bool | ssl.SSLContext:
    global _warnings_suppressed

    if verify_setting is False:
        if not _warnings_suppressed:
            try:
                import urllib3  # type: ignore[import-not-found]

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except ImportError:
                pass
            _warnings_suppressed = True
            logger.debug("TLS verification disabled")
        return False

    if verify_setting is True:
        return True

    ctx = ssl.create_default_context(cafile=str(verify_setting))
    logger.info("TLS: using pinned certificate at %s", verify_setting)
    return ctx
