CREATE TABLE comodity (
    id VARCHAR(12) PRIMARY KEY,
    cat_id VARCHAR(12),
    denomination VARCHAR(12),
    sort INT,
    name TEXT
);

CREATE VIRTUAL TABLE comodity_search USING fts5(
    id, name
);

CREATE TABLE location (
    province_id INT,
    province_name VARCHAR(254),
    city_id INT,
    city_name VARCHAR(254),
    PRIMARY KEY (province_id, city_id)
);

CREATE VIRTUAL TABLE location_search USING fts5(
    id, name
);

CREATE VIRTUAL TABLE price_type_search USING fts5(
    id, name
)

