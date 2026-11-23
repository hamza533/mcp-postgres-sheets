-- Deterministic synthetic data: 500 customers, 120 products, 1,500 orders, ~3,750 order items.
-- Order dates are relative to the day the database is created, so "last quarter" always has data.
SELECT setseed(0.42);

INSERT INTO customers (full_name, email, country, segment, created_at)
SELECT n.fn || ' ' || n.ln,
       lower(n.fn) || '.' || lower(n.ln) || g || '@example.com',
       (ARRAY['US','US','US','GB','DE','FR','CA','AU','NL','IN','BR','JP'])[1 + floor(random() * 12)::int],
       (ARRAY['consumer','consumer','consumer','small_business','small_business','enterprise'])[1 + floor(random() * 6)::int],
       date_trunc('second', now() - make_interval(days => 740 + floor(random() * 700)::int))
FROM generate_series(1, 500) AS g
CROSS JOIN LATERAL (
    SELECT (ARRAY['Ava','Liam','Noah','Emma','Olivia','Mason','Sophia','Lucas','Mia','Ethan',
                  'Amara','Kenji','Priya','Mateo','Zara','Omar','Hana','Felix','Ines','Theo'])[1 + floor(random() * 20)::int + g * 0] AS fn,
           (ARRAY['Smith','Garcia','Chen','Patel','Mueller','Dubois','Okafor','Silva','Kowalski','Nakamura',
                  'Haddad','Jensen','Rossi','Novak','Kim','Ali','Brown','Lopez','Wilson','Singh'])[1 + floor(random() * 20)::int + g * 0] AS ln
) AS n;

INSERT INTO products (sku, name, category, unit_price, active)
SELECT 'SKU-' || lpad(g::text, 4, '0'),
       a.adj || ' ' || CASE c.cat
           WHEN 'Electronics' THEN (ARRAY['Headphones','Monitor','Keyboard','Webcam','Charger'])[1 + (g / 6) % 5]
           WHEN 'Office'      THEN (ARRAY['Desk Lamp','Notebook Set','Chair','Stapler','Organizer'])[1 + (g / 6) % 5]
           WHEN 'Home'        THEN (ARRAY['Kettle','Blender','Throw Blanket','Vase','Cookware Set'])[1 + (g / 6) % 5]
           WHEN 'Outdoor'     THEN (ARRAY['Tent','Backpack','Water Bottle','Camping Stove','Hammock'])[1 + (g / 6) % 5]
           WHEN 'Fitness'     THEN (ARRAY['Yoga Mat','Dumbbell Set','Jump Rope','Foam Roller','Resistance Bands'])[1 + (g / 6) % 5]
           ELSE                    (ARRAY['Cookbook','Novel','Field Guide','Atlas','Planner'])[1 + (g / 6) % 5]
       END,
       c.cat,
       round((5 + random() * 495)::numeric, 2),
       random() > 0.08
FROM generate_series(1, 120) AS g
CROSS JOIN LATERAL (SELECT (ARRAY['Electronics','Office','Home','Outdoor','Fitness','Books'])[1 + g % 6] AS cat) AS c
CROSS JOIN LATERAL (SELECT (ARRAY['Compact','Pro','Classic','Smart','Eco','Ultra','Travel','Deluxe','Mini','Heavy-duty'])[1 + (g / 30 + g) % 10] AS adj) AS a;

INSERT INTO orders (customer_id, status, ordered_at, shipped_at)
SELECT o.c_id,
       o.st,
       o.ts,
       CASE WHEN o.st IN ('shipped', 'delivered', 'refunded')
            THEN o.ts + make_interval(days => 1 + floor(random() * 4)::int) END
FROM (
    SELECT 1 + floor(power(random(), 1.6) * 500)::int AS c_id,
           (ARRAY['delivered','delivered','delivered','delivered','shipped','paid','pending','cancelled','refunded'])[1 + floor(random() * 9)::int] AS st,
           date_trunc('second', now() - make_interval(days => floor(random() * 730)::int, secs => floor(random() * 86400)::int)) AS ts
    FROM generate_series(1, 1500) AS g
    ORDER BY g
) AS o;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.id, p.id, r.qty, p.unit_price
FROM orders o
CROSS JOIN LATERAL generate_series(1, 1 + (o.id * 7 % 4)) AS line
CROSS JOIN LATERAL (
    SELECT 1 + floor(random() * 5)::int + line * 0 AS qty,
           1 + floor(random() * 120)::int + line * 0 AS pid
) AS r
JOIN products p ON p.id = r.pid
ORDER BY o.id, line;

INSERT INTO internal.employees (full_name, salary_usd)
VALUES ('Synthetic Person A', 98000), ('Synthetic Person B', 120500);

ANALYZE;
