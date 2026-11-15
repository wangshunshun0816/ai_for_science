"""Initial migration for the isolated CandidateHypothesis test slice."""

VERSION = 1
MIGRATION = """
BEGIN IMMEDIATE;
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
PRAGMA user_version = 1;
COMMIT;
"""
