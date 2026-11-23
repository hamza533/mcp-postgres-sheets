-- Synthetic e-commerce schema used by the demo, the tests and the evaluation.
-- All data is generated (see seed.sql); nothing here is real customer data.

CREATE TABLE customers (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name   text        NOT NULL,
    email       text        NOT NULL UNIQUE,
    country     text        NOT NULL,
    segment     text        NOT NULL CHECK (segment IN ('consumer', 'small_business', 'enterprise')),
    created_at  timestamptz NOT NULL
);
COMMENT ON TABLE  customers            IS 'People and companies that have placed orders.';
COMMENT ON COLUMN customers.full_name  IS 'Customer display name (synthetic).';
COMMENT ON COLUMN customers.email      IS 'Contact email (synthetic, example.com).';
COMMENT ON COLUMN customers.country    IS 'ISO 3166-1 alpha-2 country code.';
COMMENT ON COLUMN customers.segment    IS 'consumer, small_business or enterprise.';
COMMENT ON COLUMN customers.created_at IS 'When the customer account was created.';

CREATE TABLE products (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku         text           NOT NULL UNIQUE,
    name        text           NOT NULL,
    category    text           NOT NULL,
    unit_price  numeric(10, 2) NOT NULL CHECK (unit_price > 0),
    active      boolean        NOT NULL DEFAULT true
);
COMMENT ON TABLE  products            IS 'Catalogue of products for sale.';
COMMENT ON COLUMN products.sku        IS 'Stock keeping unit, unique per product.';
COMMENT ON COLUMN products.category   IS 'Product category: Electronics, Office, Home, Outdoor, Fitness or Books.';
COMMENT ON COLUMN products.unit_price IS 'Current list price in USD.';
COMMENT ON COLUMN products.active     IS 'False when the product is discontinued.';

CREATE TABLE orders (
    id           integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id  integer     NOT NULL REFERENCES customers (id),
    status       text        NOT NULL CHECK (status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled', 'refunded')),
    ordered_at   timestamptz NOT NULL,
    shipped_at   timestamptz
);
CREATE INDEX orders_customer_id_idx ON orders (customer_id);
CREATE INDEX orders_ordered_at_idx  ON orders (ordered_at);
COMMENT ON TABLE  orders            IS 'One row per order. Revenue lives in order_items.';
COMMENT ON COLUMN orders.status     IS 'pending, paid, shipped, delivered, cancelled or refunded. Exclude cancelled and refunded orders from revenue.';
COMMENT ON COLUMN orders.ordered_at IS 'When the order was placed.';
COMMENT ON COLUMN orders.shipped_at IS 'When the order left the warehouse; null if not shipped yet.';

CREATE TABLE order_items (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id    integer        NOT NULL REFERENCES orders (id),
    product_id  integer        NOT NULL REFERENCES products (id),
    quantity    integer        NOT NULL CHECK (quantity > 0),
    unit_price  numeric(10, 2) NOT NULL CHECK (unit_price > 0)
);
CREATE INDEX order_items_order_id_idx   ON order_items (order_id);
CREATE INDEX order_items_product_id_idx ON order_items (product_id);
COMMENT ON TABLE  order_items            IS 'Line items. Line revenue = quantity * unit_price.';
COMMENT ON COLUMN order_items.unit_price IS 'Price actually charged per unit at order time (USD).';

CREATE VIEW order_totals AS
SELECT o.id AS order_id,
       o.customer_id,
       o.status,
       o.ordered_at,
       sum(oi.quantity * oi.unit_price)::numeric(12, 2) AS total_usd
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
GROUP BY o.id;
COMMENT ON VIEW order_totals IS 'Order value per order (sum of its line items), all statuses.';

-- A schema the MCP server must never expose: not in ALLOWED_SCHEMAS and no grant to the read-only role.
CREATE SCHEMA internal;
CREATE TABLE internal.employees (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name   text           NOT NULL,
    salary_usd  numeric(10, 2) NOT NULL
);
