"""Initial migration for the isolated CandidateHypothesis test slice."""

import sqlite3

VERSION = 2
INITIAL_SCHEMA = """
CREATE TABLE account (
    id TEXT PRIMARY KEY, revision INTEGER NOT NULL, login_subject TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL UNIQUE, tenant_revision INTEGER NOT NULL,
    UNIQUE(id, revision),
    FOREIGN KEY (tenant_id, tenant_revision, id, revision)
        REFERENCES tenant(id, revision, account_id, account_revision)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE tenant (
    id TEXT PRIMARY KEY, revision INTEGER NOT NULL, account_id TEXT NOT NULL UNIQUE,
    account_revision INTEGER NOT NULL,
    UNIQUE(id, revision),
    UNIQUE(id, revision, account_id, account_revision),
    FOREIGN KEY (account_id, account_revision) REFERENCES account(id, revision)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE project (
    tenant_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
    tenant_revision INTEGER NOT NULL,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, tenant_revision) REFERENCES tenant(id, revision)
);
CREATE TABLE candidate_version (
    tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, object_id TEXT NOT NULL,
    content_version TEXT NOT NULL, digest TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, object_id, content_version),
    FOREIGN KEY (tenant_id, project_id) REFERENCES project(tenant_id, id)
);
"""


BINDING_MIGRATION = """
CREATE TABLE artifact_binding (
    tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, object_id TEXT NOT NULL,
    content_version TEXT NOT NULL, digest TEXT NOT NULL UNIQUE,
    PRIMARY KEY (tenant_id, project_id, object_id, content_version),
    UNIQUE(tenant_id, project_id, object_id, content_version, digest),
    FOREIGN KEY (tenant_id, project_id) REFERENCES project(tenant_id, id)
);
DROP TABLE candidate_version;
CREATE TABLE candidate_version (
    tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, object_id TEXT NOT NULL,
    content_version TEXT NOT NULL, digest TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, object_id, content_version),
    FOREIGN KEY (tenant_id, project_id) REFERENCES project(tenant_id, id),
    FOREIGN KEY (tenant_id, project_id, object_id, content_version, digest)
        REFERENCES artifact_binding(tenant_id, project_id, object_id, content_version, digest)
);
PRAGMA user_version = 2;
"""


def migrate(db: sqlite3.Connection) -> None:
    # Execute each statement under one lock so an unchecked v1 row cannot arrive
    # between the empty-table check and the schema change.
    db.execute("BEGIN IMMEDIATE")
    with db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == VERSION:
            return
        if version == 0:
            for statement in INITIAL_SCHEMA.strip().rstrip(";").split(";"):
                db.execute(statement)
        elif version != 1:
            raise ValueError("Unsupported migration revision")
        if db.execute("SELECT 1 FROM candidate_version LIMIT 1").fetchone() is not None:
            raise ValueError("V1 candidates lack artifact bindings; start a fresh test run")
        for statement in BINDING_MIGRATION.strip().rstrip(";").split(";"):
            db.execute(statement)
