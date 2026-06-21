"""Authentication: accounts and bearer tokens, built as ports-and-adapters.

Public surface:

* :class:`AuthService` -- registration, login, and token issue/verify policy.
* :class:`UserStore` (:mod:`ragproject.core.auth.ports`) -- the store abstraction.
* :class:`InMemoryUserStore` -- the default store and test double. The Postgres
  store is imported only where it is wired (:mod:`ragproject.api.deps`), to keep
  this package import light.
"""

from ragproject.core.auth.adapters.store_memory import InMemoryUserStore
from ragproject.core.auth.models import User
from ragproject.core.auth.ports import UserStore
from ragproject.core.auth.service import AuthService, EmailAlreadyRegistered

__all__ = [
    "AuthService",
    "EmailAlreadyRegistered",
    "InMemoryUserStore",
    "User",
    "UserStore",
]
