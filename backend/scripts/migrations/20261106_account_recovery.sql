-- Additive recovery schema. No automatic email, device, credit or profile backfill.
-- Review and apply only to an explicitly selected database. Idempotent DDL.
BEGIN;

CREATE TABLE IF NOT EXISTS verified_account_emails (
	account_id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	PRIMARY KEY (account_id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS account_sessions (
	token_hash VARCHAR(64) NOT NULL, 
	account_id INTEGER NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(account_id) REFERENCES accounts (id)
);

CREATE INDEX IF NOT EXISTS ix_account_sessions_account_id ON account_sessions (account_id);

CREATE TABLE IF NOT EXISTS account_challenges (
	id VARCHAR(64) NOT NULL, 
	code_hash VARCHAR(64) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	purpose VARCHAR(12) NOT NULL, 
	account_id INTEGER, 
	device_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	consumed BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id)
);

CREATE TABLE IF NOT EXISTS account_rate_limits (
	key VARCHAR(64) NOT NULL, 
	count INTEGER NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE IF NOT EXISTS ziwei_profile_owners (
	profile_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	PRIMARY KEY (profile_id), 
	FOREIGN KEY(profile_id) REFERENCES ziwei_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(account_id) REFERENCES accounts (id)
);

CREATE INDEX IF NOT EXISTS ix_ziwei_profile_owners_account_id ON ziwei_profile_owners (account_id);

COMMIT;
