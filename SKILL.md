---
name: indonesian-commodity-and-food-resilience
description: Retrieve and analyze Indonesian commodity prices (harga pangan/sembako) and regional food resilience statistics (statistik ketahanan pangan). Make sure to use this skill whenever the user asks about the price of rice, sugar, meat, or any other food commodity in Indonesia, OR when the user asks about food security, food vulnerability, and resilience (ketahanan pangan) at the regional or village level across specific years.
---

# Indonesian Commodity Prices & Food Resilience

This skill allows you to retrieve real-time and historical commodity prices using the PHIPS service, as well as regional food resilience statistics using the Badan Pangan service.

## When to Use
Trigger this skill whenever a user asks about:
- The current price of a specific food item or commodity in Indonesia.
- Price comparisons between different dates (e.g., "Harga beras bulan lalu vs sekarang").
- Price trends in specific locations (e.g., "Harga cabai di Jawa Timur").
- Food resilience or food security statistics (e.g., "Statistik ketahanan pangan di Jakarta", "Desa rentan pangan di Banten tahun 2023").

## Available Tools & Workflow

### 1. Commodity Prices Workflow (`get_comodity_prices`)
The primary workhorse for pricing data. It is smart enough to handle fuzzy matching for commodities and locations.
- **Direct Search (Preferred):** Use `get_comodity_prices` by passing a `comodity_keyword` and a `location_keyword`.
- **Exploration:** If the user is unsure about what commodities are tracked, use `list_comodities`. For supported regions, use `list_location`.
- **Price Types:** By default, use `price_type_id: 2` (usually retail/consumer price) unless specified otherwise. Use `list_price_type` to find exact IDs for wholesale or producer prices.

### 2. Food Resilience Workflow (`get_statistik_wilayah_ketahanan_pangan`)
Use this tool to get statistical information about food resilience (ketahanan pangan) for each village (Desa/Kelurahan) within a specific region.
- **Usage:** Pass a `location_keyword` (e.g., "Jakarta") and a year`year` (e.g., `2023`).
- **Data Availability Note:** The statistical data for the current active year is usually NOT yet available. If the user does not specify a year, default to checking the previous 1 or 2 years.

## Data Interpretation Rules
- **Commodity Prices (`matched` and `results`):** Always verify what exact location and commodity variants were matched. Parse the time-series `results` array and summarize the trend in a readable format rather than dumping raw JSON.
- **Food Resilience Statistics:** When interpreting Badan Pangan statistics, analyze the village-level data to provide a high-level summary of the region's food security status. Highlight extremes, such as villages with the highest vulnerability or the strongest resilience, if applicable.

## Formatting Rules
- **Dates:** When passing dates to `start_date` or `end_date` in price queries, ALWAYS use the `YYYY-MM-DD` format (e.g., `2026-04-28`).
- **Year:** When passing year to `get_statistik_wilayah_ketahanan_pangan`, use a JSON array of integers (e.g., `2023`).