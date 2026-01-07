CREATE DATABASE popup;
\c popup;

CREATE TABLE popup_stores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, crawled_at)
);

CREATE INDEX idx_crawled_at ON popup_stores(crawled_at);