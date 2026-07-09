"""Console helpers kept internal to taxonorm."""

from __future__ import annotations

import warnings


def wrn(message: str) -> None:
    warnings.warn(str(message), UserWarning, stacklevel=2)
