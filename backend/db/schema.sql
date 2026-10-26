DROP TABLE IF EXISTS order_items, orders, books, customers;

CREATE TABLE customers (
    id    integer PRIMARY KEY,
    name  text NOT NULL,
    email text NOT NULL UNIQUE
);

CREATE TABLE books (
    id        integer PRIMARY KEY,
    title     text NOT NULL,
    author    text NOT NULL,
    section   text NOT NULL CHECK (section IN ('classic-novels', 'adventure-sci-fi', 'philosophy', 'self-help')),
    is_signed boolean NOT NULL DEFAULT false,
    price     numeric(8, 2) NOT NULL,  -- current list price; changes over time
    stock     integer NOT NULL DEFAULT 0  -- not used until write actions (slice 2)
);

CREATE TABLE orders (
    id              integer PRIMARY KEY,
    customer_id     integer NOT NULL REFERENCES customers (id),
    status          text NOT NULL CHECK (status IN ('processing', 'shipped', 'delivered')),
    shipping_method text NOT NULL CHECK (shipping_method IN ('standard', 'express')),
    shipping_cost   numeric(8, 2) NOT NULL,
    promotion       text CHECK (promotion IN ('jules-verne-discount', 'self-help-discount', 'buy-5-get-the-cheapest-free')),
    created_at      timestamptz NOT NULL,
    shipped_at      timestamptz,
    delivered_at    timestamptz
);

-- Prices are snapshotted per line at purchase time, so refunds don't depend on today's books.price.
CREATE TABLE order_items (
    order_id   integer NOT NULL REFERENCES orders (id),
    book_id    integer NOT NULL REFERENCES books (id),
    unit_price numeric(8, 2) NOT NULL,
    discount   numeric(8, 2) NOT NULL DEFAULT 0,
    paid       numeric(8, 2) NOT NULL,
    PRIMARY KEY (order_id, book_id)
);
