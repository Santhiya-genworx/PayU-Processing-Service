"""Module: runner.py"""
from __future__ import annotations
 
import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
 
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
 
 
_logger = logging.getLogger("uvicorn.error")
_MIGRATION_FILE_RE = re.compile(r"^(?P<version_number>\d{8,14})_(?P<name>[a-z0-9_]+)\.sql$")
_DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parent / "versions"
 
 
@dataclass(frozen=True, slots=True)
class MigrationFile:
    """Represents a database migration file with its metadata. This dataclass is used to store information about each migration file, including its unique identifier (derived from the filename), version number, name, checksum of the SQL content, the raw SQL string, and the file path. The identifier is typically a combination of the version number and name, ensuring uniqueness across migrations. The checksum is computed using SHA-256 to allow for integrity checks when validating applied migrations against their corresponding files. This class is immutable and uses slots for memory efficiency."""
    identifier: str
    version_number: str
    name: str
    checksum: str
    sql: str
    path: Path
 
 
def discover_migrations(migrations_dir: Path | None = None) -> list[MigrationFile]:
    """Discovers migration files in the specified directory. This function looks for SQL files in the given directory (or the default migrations directory if none is provided) that match the expected filename pattern of '<version_number>_<name>.sql'. It validates that each file has a unique identifier, is not empty, and computes a checksum for the contents of the file. The function returns a list of MigrationFile objects representing the discovered migrations, sorted by their version numbers. If any issues are found with the migration files (such as invalid filenames, duplicates, or empty files), appropriate exceptions are raised with details about the problem."""    
    directory = migrations_dir or _DEFAULT_MIGRATIONS_DIR
    if not directory.exists():
        raise FileNotFoundError(f"Migration directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Migration path is not a directory: {directory}")
 
    migrations: list[MigrationFile] = []
    seen_identifiers: set[str] = set()
 
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_FILE_RE.match(path.name)
        if not match:
            raise ValueError(
                "Invalid migration filename "
                f"{path.name!r}. Expected '<version>_<name>.sql' with lowercase snake_case."
            )
 
        identifier = path.stem
        if identifier in seen_identifiers:
            raise ValueError(f"Duplicate migration identifier found: {identifier}")
        seen_identifiers.add(identifier)
 
        sql = path.read_text(encoding="utf-8").strip()
        if not sql:
            raise ValueError(f"Migration file is empty: {path}")
 
        migrations.append(
            MigrationFile(
                identifier=identifier,
                version_number=match.group("version_number"),
                name=match.group("name"),
                checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                sql=sql,
                path=path,
            )
        )
 
    return migrations
 
 
async def apply_migrations(
    conn: AsyncConnection,
    migrations_dir: Path | None = None,
) -> None:
    """Applies pending database migrations in order. This function discovers migration files in the specified directory, checks which migrations have already been applied by querying the schema_migrations table, and applies any new migrations in order of their version numbers. It ensures that the schema_migrations table exists before checking for applied migrations and validates the integrity of already applied migrations by comparing checksums. If a migration file has been altered after being applied (checksum mismatch), it raises a RuntimeError to prevent potential issues. If any errors occur during the database operations, they will be raised and can be handled by the calling function.   This function is typically called during the initialization of the database connection to ensure that the database schema is up to date before handling any application logic.  """
    migrations = discover_migrations(migrations_dir)
    await _ensure_schema_migrations_table(conn)
 
    result = await conn.execute(
        text(
            """
            SELECT version, version_number, name, checksum
            FROM schema_migrations
            """
        )
    )
    applied = {
        row.version: {
            "version_number": row.version_number,
            "name": row.name,
            "checksum": row.checksum,
        }
        for row in result
    }
 
    for migration in migrations:
        existing = applied.get(migration.identifier)
        if existing is not None:
            await _validate_or_backfill_migration_record(conn, migration, existing)
            continue
 
        statements = _split_sql_statements(migration.sql)
        if not statements:
            raise ValueError(f"Migration {migration.identifier} contains no executable SQL statements.")
 
        _logger.info("Applying DB migration: %s", migration.identifier)
        for statement in statements:
            await conn.exec_driver_sql(statement)
 
        await conn.execute(
            text(
                """
                INSERT INTO schema_migrations (version, version_number, name, checksum)
                VALUES (:version, :version_number, :name, :checksum)
                """
            ),
            {
                "version": migration.identifier,
                "version_number": migration.version_number,
                "name": migration.name,
                "checksum": migration.checksum,
            },
        )
        _logger.info("Applied DB migration: %s", migration.identifier)
 
 
async def _ensure_schema_migrations_table(conn: AsyncConnection) -> None:
    """Ensures that the schema_migrations table exists in the database. This table is used to track which migrations have been applied, along with their version numbers, names, and checksums. If the table does not exist, it will be created. If the table already exists but is missing any of the expected columns (version_number, name, checksum), those columns will be added. This function is called at the beginning of the apply_migrations function to ensure that the migration tracking infrastructure is in place before attempting to apply any migrations. If any errors occur during the database operations, they will be raised and can be handled by the calling function."""
    await conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(128) PRIMARY KEY,
            version_number VARCHAR(32),
            name VARCHAR(255),
            checksum VARCHAR(64),
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    await conn.exec_driver_sql(
        "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS version_number VARCHAR(32)"
    )
    await conn.exec_driver_sql(
        "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS name VARCHAR(255)"
    )
    await conn.exec_driver_sql(
        "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS checksum VARCHAR(64)"
    )
 
 
async def _validate_or_backfill_migration_record(
    conn: AsyncConnection,
    migration: MigrationFile,
    existing: dict[str, str | None],
) -> None:
    """Validates that an already applied migration has the same checksum as the current migration file. If the version_number and name are missing from the existing record, it backfills them from the migration file. If there is a checksum mismatch, it raises a RuntimeError to prevent potential issues from an altered migration file. This function ensures the integrity of applied migrations and helps maintain a consistent state of the database schema. If any errors occur during the database operations, they will be raised and can be handled by the calling function. """
    checksum = existing.get("checksum")
    if checksum:
        if checksum != migration.checksum:
            raise RuntimeError(
                "Migration checksum mismatch for "
                f"{migration.identifier}. Refusing to continue because an applied SQL file changed."
            )
        if existing.get("version_number") and existing.get("name"):
            return
 
    await conn.execute(
        text(
            """
            UPDATE schema_migrations
            SET version_number = COALESCE(version_number, :version_number),
                name = COALESCE(name, :name),
                checksum = COALESCE(checksum, :checksum)
            WHERE version = :version
            """
        ),
        {
            "version": migration.identifier,
            "version_number": migration.version_number,
            "name": migration.name,
            "checksum": migration.checksum,
        },
    )
 
 
def _split_sql_statements(sql: str) -> list[str]:
    """Splits a SQL string into individual statements, correctly handling semicolons within strings, comments, and dollar-quoted sections. Returns a list of executable SQL statements without trailing semicolons. This function uses a state machine approach to track whether the current position is within a single-quoted string, double-quoted string, line comment, block comment, or dollar-quoted section, ensuring that semicolons are only treated as statement separators when they are outside of these contexts. If the input SQL string is empty or contains only whitespace, it returns an empty list. If any statements are found, they are stripped of leading and trailing whitespace before being returned in the list."""
    statements: list[str] = []
    current: list[str] = []
    i = 0
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    dollar_quote: str | None = None
 
    while i < len(sql):
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < len(sql) else ""
 
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                current.append(char)
            i += 1
            continue
 
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
 
        if dollar_quote is not None:
            if sql.startswith(dollar_quote, i):
                current.append(dollar_quote)
                i += len(dollar_quote)
                dollar_quote = None
                continue
            current.append(char)
            i += 1
            continue
 
        if in_single_quote:
            current.append(char)
            if char == "'" and next_char == "'":
                current.append(next_char)
                i += 2
                continue
            if char == "'":
                in_single_quote = False
            i += 1
            continue
 
        if in_double_quote:
            current.append(char)
            if char == '"' and next_char == '"':
                current.append(next_char)
                i += 2
                continue
            if char == '"':
                in_double_quote = False
            i += 1
            continue
 
        if char == "-" and next_char == "-":
            in_line_comment = True
            i += 2
            continue
 
        if char == "/" and next_char == "*":
            in_block_comment = True
            i += 2
            continue
 
        if char == "'":
            in_single_quote = True
            current.append(char)
            i += 1
            continue
 
        if char == '"':
            in_double_quote = True
            current.append(char)
            i += 1
            continue
 
        if char == "$":
            tag_end = sql.find("$", i + 1)
            if tag_end != -1:
                candidate = sql[i : tag_end + 1]
                if re.fullmatch(r"\$[A-Za-z0-9_]*\$", candidate):
                    dollar_quote = candidate
                    current.append(candidate)
                    i = tag_end + 1
                    continue
 
        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            i += 1
            continue
 
        current.append(char)
        i += 1
 
    trailing_statement = "".join(current).strip()
    if trailing_statement:
        statements.append(trailing_statement)
    return statements
 
 