-- Reference data aligned with docs/reference/inventory-tracker.xlsx (production abbreviations).
-- UPC columns are NULL until Cole provides bottle / 4-pack / case examples.

INSERT INTO brands (name, is_active)
VALUES
    ('Polly''s Pop', TRUE),
    ('Pioneer', FALSE),
    ('Polly-Q', FALSE)
ON CONFLICT (name) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO products (brand_id, name, flavor_code, is_diet, upc_bottle, upc_4pack, upc_case, is_active)
SELECT b.id, v.name, v.flavor_code, v.is_diet, NULL, NULL, NULL, TRUE
FROM brands b
CROSS JOIN (
    VALUES
        ('Root Beer', 'RB', FALSE),
        ('Strawberry', 'ST', FALSE),
        ('Orange', 'OR', FALSE),
        ('Cream', 'CR', FALSE),
        ('Black Cherry', 'BC', FALSE),
        ('Grape', 'GR', FALSE),
        ('Pineapple', 'PI', FALSE),
        ('Blue Raspberry', 'BR', FALSE),
        ('Donut', 'DO', FALSE),
        ('Peach', 'PE', FALSE),
        ('Ginger Beer', 'GB', FALSE),
        ('Diet Root Beer', 'DRB', TRUE),
        ('Diet Strawberry', 'DST', TRUE),
        ('Diet Orange', 'DOR', TRUE),
        ('Diet Cream', 'DCR', TRUE),
        ('Diet Black Cherry', 'DBC', TRUE)
) AS v(name, flavor_code, is_diet)
WHERE b.name = 'Polly''s Pop'
ON CONFLICT (brand_id, name) DO UPDATE SET
    flavor_code = EXCLUDED.flavor_code,
    is_diet = EXCLUDED.is_diet;

INSERT INTO products (brand_id, name, flavor_code, is_diet, upc_bottle, upc_4pack, upc_case, is_active)
SELECT b.id, v.name, v.flavor_code, FALSE, NULL, NULL, NULL, TRUE
FROM brands b
CROSS JOIN (
    VALUES
        ('Original', 'ORW'),
        ('Black Cherry', 'BCW'),
        ('Mixed Berry', 'MBW'),
        ('Lemon', 'LEW')
) AS v(name, flavor_code)
WHERE b.name = 'Pioneer'
ON CONFLICT (brand_id, name) DO UPDATE SET
    flavor_code = EXCLUDED.flavor_code;

INSERT INTO products (brand_id, name, flavor_code, is_diet, upc_bottle, upc_4pack, upc_case, is_active)
SELECT b.id, v.name, v.flavor_code, FALSE, NULL, NULL, NULL, TRUE
FROM brands b
CROSS JOIN (
    VALUES
        ('Root Beer', 'RB'),
        ('Pineapple', 'PI'),
        ('Peach', 'PE')
) AS v(name, flavor_code)
WHERE b.name = 'Polly-Q'
ON CONFLICT (brand_id, name) DO UPDATE SET
    flavor_code = EXCLUDED.flavor_code;
