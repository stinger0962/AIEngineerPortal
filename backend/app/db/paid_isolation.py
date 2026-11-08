"""Pure database identity checks; no settings, dotenv, models or connections."""
from pathlib import Path
from ipaddress import ip_address
import re

from sqlalchemy.engine import make_url


class DatabaseIsolationError(RuntimeError):
    """Fixed, credential-free configuration error."""


def _sqlite_database_path(url):
    # URI/query options can disguise the target file (file:.../mode/uri/etc.).
    # This entrypoint only accepts ordinary persistent SQLite paths.
    if (url.query or not url.database or url.database == ":memory:"
            or url.database.startswith("file:") or url.host or url.username or url.password):
        raise DatabaseIsolationError("Use plain dedicated SQLite file paths without URI options")
    return Path(url.database).resolve()


def _postgres_identity(url):
    host = (url.host or "").lower().rstrip(".")
    if not host or not url.database:
        raise DatabaseIsolationError("Use an explicit PostgreSQL host and database")
    # A single schema selector cannot redirect libpq to a different host/database.
    # Reject duplicate values, additional switches and connection overrides.
    if url.query and (set(url.query) != {"options"}
            or not isinstance(url.query["options"], str)
            or not re.fullmatch(r"-csearch_path=[A-Za-z_][A-Za-z0-9_]{0,62}", url.query["options"])):
        raise DatabaseIsolationError("Only a single safe PostgreSQL search_path option is supported")
    try:
        host = ip_address(host).compressed
    except ValueError:
        pass  # DNS names are compared without resolving or contacting a server.
    return host, url.port or 5432, url.database


def validate_database_isolation(paid_raw, portal_raw):
    """Reject common aliases before either configured database is opened."""
    try:
        paid, portal = make_url(paid_raw), make_url(portal_raw)
        if paid == portal:
            raise DatabaseIsolationError("Paid product must not use the portal DATABASE_URL")
        paths = {}
        identities = {}
        for label, url in (("paid", paid), ("portal", portal)):
            if url.get_backend_name() == "sqlite":
                paths[label] = _sqlite_database_path(url)
            elif url.get_backend_name() == "postgresql":
                identities[label] = _postgres_identity(url)
        same_file = len(paths) == 2 and (
            paths["paid"] == paths["portal"] or (
                paths["paid"].exists() and paths["portal"].exists()
                and paths["paid"].samefile(paths["portal"])))
        same_postgres = len(identities) == 2 and identities["paid"] == identities["portal"]
        if same_file or same_postgres:
            raise DatabaseIsolationError("Paid product must not use the portal DATABASE_URL")
    except DatabaseIsolationError:
        raise
    except Exception:
        # Never echo a malformed URL, password, or filesystem details.
        raise DatabaseIsolationError("Invalid dedicated database configuration") from None


