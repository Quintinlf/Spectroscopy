"""Auto-discovery of MediaProcessor plugins.

Scans config.PROCESSORS_PACKAGE (default: the processors/ package) for any
concrete MediaProcessor subclass and instantiates it. Adding a new processor
(ImageProcessor, AudioProcessor, GifProcessor, PDFProcessor, ...) means
dropping one new module into that package -- this function, and everything
that calls it, needs zero changes.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Optional

import config
from processing import MediaProcessor

logger = logging.getLogger("media_guardian.plugins")


def discover_processors(package_name: Optional[str] = None) -> list[MediaProcessor]:
    """Import every module in package_name and instantiate each concrete
    MediaProcessor subclass found."""
    package_name = package_name or config.PROCESSORS_PACKAGE
    package = importlib.import_module(package_name)

    discovered: list[MediaProcessor] = []
    seen_classes: set[type] = set()

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, prefix=f"{package_name}."):
        if is_pkg:
            continue
        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.exception("Could not import processor module %s; skipping it.", module_name)
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is MediaProcessor or not issubclass(obj, MediaProcessor) or inspect.isabstract(obj):
                continue
            if obj in seen_classes:
                continue
            seen_classes.add(obj)
            try:
                discovered.append(obj())
            except Exception:
                logger.exception("Could not instantiate processor %s; skipping it.", obj.__name__)

    if not discovered:
        logger.warning("No MediaProcessor plugins were discovered in %s.", package_name)
    return discovered
