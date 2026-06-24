CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    password_hash TEXT,
    auth_provider TEXT NOT NULL DEFAULT 'email',
    provider_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_oauth
    ON users (auth_provider, provider_id)
    WHERE provider_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cart_user ON cart_items(user_id);
