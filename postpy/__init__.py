"""
PostPy - A Postman-style API testing and automation tool
"""

__version__ = "1.4.0"

from .client import PostPy  # noqa: E402
from .core import Collection, CollectionLoader, CollectionRunner, Request  # noqa: E402

__all__ = [
    "Collection",
    "CollectionLoader",
    "CollectionRunner",
    "PostPy",
    "Request",
    "__version__",
]
