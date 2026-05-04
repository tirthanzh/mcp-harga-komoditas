---
name: indonesian-commodity-prices
description: Retrieve and analyze Indonesian commodity and food prices (harga pangan/sembako) across various locations and timeframes. Make sure to use this skill whenever the user asks about the price of rice (beras), sugar, meat, chili, or any other food commodity in Indonesia, or wants to compare inflation, track price trends over time, or check prices in specific provinces/cities (e.g., Jakarta, Bandung).
---

# Indonesian Commodity Prices

This skill allows you to retrieve real-time and historical commodity prices in Indonesia using the PHIPS service. 

## When to Use
Trigger this skill whenever a user asks about:
- The current price of a specific food item or commodity in Indonesia.
- Price comparisons between different dates (e.g., "Harga beras bulan lalu vs sekarang").
- Price trends in specific locations (e.g., "Harga cabai di Jawa Timur").

## Available Tools & Workflow

The primary workhorse is `get_comodity_prices`. It is smart enough to handle fuzzy matching for commodities and locations. 

**Workflow Guidelines:**
1. **Direct Search (Preferred):** You can directly use `get_comodity_prices` by passing a `comodity_keyword` (e.g., "beras") and a `location_keyword` (e.g., "jakarta"). The tool will automatically gather the matched commodity variants and locations, and return the aggregated price table.
2. **Exploration:** If the user is unsure about what commodities are tracked, use `list_comodities`. If they want to see supported regions, use `list_location`.
3. **Price Types:** By default, use `price_type_id: 2` (usually retail/consumer price) unless specified otherwise. Use `list_price_type` if you need to find the exact ID for wholesale or producer prices.

## Data Interpretation Rules
When you receive the output from `get_comodity_prices`:
- **`matched` object:** Always verify what exact location and commodity variants were matched. For example, "Beras" might match "Beras Kualitas Bawah", "Beras Kualitas Medium", etc.
- **`results` array:** This contains the time-series data. The keys are dates (e.g., `"28/04/2026"`), and the values are the prices formatted as strings (e.g., `"17,100"`). 
- **Analysis:** Don't just dump the JSON to the user. Parse the `results` array and summarize the trend (e.g., "Harga Beras Kualitas Super I stabil di Rp21.250 selama seminggu terakhir di Kota Jakarta Pusat").

## Date Formatting
When passing dates to `start_date` or `end_date`, ALWAYS use the `YYYY-MM-DD` format (e.g., `2026-04-28`).