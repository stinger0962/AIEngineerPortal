-- Additive PostgreSQL migration. Run ONLY against a separately provisioned TEST DB.
-- Application Base.metadata.create_all also creates this table on fresh databases.
-- No existing production data or schema was migrated by this implementation.
BEGIN;
CREATE TABLE IF NOT EXISTS billing_requests (
    key VARCHAR(64) PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    fingerprint VARCHAR(64) NOT NULL,
    response_json JSON NOT NULL
);
COMMIT;
-- Rollback (only after test traffic is stopped): DROP TABLE billing_requests;
-- Removing this table destroys retry protection; never do so during active traffic.
