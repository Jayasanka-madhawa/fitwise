CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    brand TEXT,
    department TEXT,
    department_final TEXT,
    price_usd NUMERIC(10, 2),
    price NUMERIC(12, 2) NOT NULL,      -- LKR
    currency TEXT DEFAULT 'LKR',
    average_rating NUMERIC(3, 2),
    review_count INTEGER,
    popularity_score NUMERIC(10, 4),
    features TEXT,
    description TEXT,
    image_url TEXT,
    main_category TEXT
);

CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    product_id TEXT REFERENCES products(product_id) ON DELETE CASCADE,
    rating NUMERIC(2, 1),
    review_title TEXT,
    review_text TEXT,
    helpful_vote INTEGER DEFAULT 0,
    verified_purchase BOOLEAN,
    review_time TIMESTAMPTZ,
    user_id TEXT
);

CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    product_id TEXT REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1 CHECK (quantity > 0),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, product_id)
);

CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_dept ON products(department_final);
CREATE INDEX idx_products_popularity ON products(popularity_score DESC);
CREATE INDEX idx_products_title ON products USING gin (title gin_trgm_ops);
CREATE INDEX idx_reviews_product ON reviews(product_id);