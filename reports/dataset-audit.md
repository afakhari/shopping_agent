# Dataset audit report (automatically generated)

- Source: `starcoach-dataset-v16-cap300-csv.zip`
- Generated at: `2026-10-21T20:57:54.033311+00:00`
- Price outlier threshold (Toman): `100000000000`

## Table counts

| File | Rows | Unique IDs | Duplicate IDs | Missing IDs | Invalid JSON cells |
|---|---:|---:|---:|---:|---:|
| `products.csv` | 225,903 | 225,903 | 0 | 0 | 0 |
| `shops.csv` | 6,476 | 6,476 | 0 | 0 | 0 |
| `offers.csv` | 331,506 | 331,506 | 0 | 0 | 0 |

## Missing-value coverage

### `products.csv`

| Column | Missing or null-like | Share |
|---|---:|---:|
| `model` | 221,847 | 98.20% |
| `brand_name` | 168,269 | 74.49% |
| `persian_title` | 2 | 0.00% |
| `category_name` | 0 | 0.00% |
| `image_urls` | 0 | 0.00% |
| `product_id` | 0 | 0.00% |
| `specs` | 0 | 0.00% |

### `shops.csv`

| Column | Missing or null-like | Share |
|---|---:|---:|
| `instagram` | 6,454 | 99.66% |
| `website_url` | 6,386 | 98.61% |
| `supports_fast_delivery` | 4,875 | 75.28% |
| `address` | 1 | 0.02% |
| `location_label` | 1 | 0.02% |
| `category_names` | 0 | 0.00% |
| `contacts` | 0 | 0.00% |
| `lat` | 0 | 0.00% |
| `lon` | 0 | 0.00% |
| `name` | 0 | 0.00% |
| `payment_options` | 0 | 0.00% |
| `shop_id` | 0 | 0.00% |
| `weekly_hours` | 0 | 0.00% |

### `offers.csv`

| Column | Missing or null-like | Share |
|---|---:|---:|
| `description` | 293,129 | 88.42% |
| `warranty` | 272,563 | 82.22% |
| `price_toman` | 15,083 | 4.55% |
| `last_price_changed_at` | 769 | 0.23% |
| `offer_id` | 0 | 0.00% |
| `product_id` | 0 | 0.00% |
| `seller_title` | 0 | 0.00% |
| `shop_id` | 0 | 0.00% |

## Product profile

| Metric | Count |
|---|---:|
| `nonempty_titles` | 225,901 |
| `nonempty_brands` | 57,634 |
| `nonempty_categories` | 225,903 |
| `nonempty_models` | 4,056 |
| `products_with_images` | 224,684 |
| `products_with_specs` | 144,599 |
| `image_urls_total` | 349,118 |
| `specs_total` | 1,227,511 |

## Shop profile

| Metric | Count |
|---|---:|
| `with_name` | 6,476 |
| `with_address` | 6,475 |
| `with_coordinates` | 6,476 |
| `with_website` | 90 |
| `with_instagram` | 22 |
| `with_pasazh_hint` | 3,651 |
| `with_floor_hint` | 4,307 |
| `with_unit_hint` | 6,014 |
| `with_weekly_hours` | 4,473 |
| `with_contact_channel` | 6,476 |
| `unique_shops_with_in_person_credit` | 82 |
| `lat_out_of_range` | 0 |
| `lon_out_of_range` | 0 |

### Payment option entries by channel

| Channel | Entries |
|---|---:|
| `in_person` | 174 |
| `unknown` | 211 |

## Offers

| Metric | Value |
|---|---:|
| `valid_prices` | 316423 |
| `null_prices` | 15083 |
| `non_positive_prices` | 0 |
| `over_threshold_prices` | 144 |
| `invalid_price_values` | 0 |
| `orphan_product_refs` | 0 |
| `orphan_shop_refs` | 0 |
| `timestamps_valid` | 330737 |
| `timestamps_invalid` | 0 |
| `timestamps_missing` | 769 |
| `oldest_price_change_utc` | 2020-12-03T08:51:32.129814+00:00 |
| `newest_price_change_utc` | 2026-10-13T00:02:35.297834+00:00 |
| `median_price_age_days_at_audit` | 30.28 |

## Relationships

| Metric | Value |
|---|---:|
| `offers_missing_product` | 0 |
| `offers_missing_shop` | 0 |
| `products_without_offer` | 0 |

> This report does not expose phone numbers or full source records. Counts describe the provided snapshot only; offers and contacts are not proof of live inventory or reachability.
