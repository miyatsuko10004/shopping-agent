---
name: shopping-search
description: Search, compare prices, and find the lowest price deals across major online shopping sites and retail stores in Japan. Use when the user asks to find the best deal, cheapest price, or compare stores for a product.
---

# Shopping Search & Lowest Price Comparator

This skill allows the agent to search across multiple Japanese shopping sites and retail stores (Amazon, Rakuten, Yahoo Shopping, Yodobashi, Bic Camera, Yamada, Edion, specialty shops, etc.) to find the lowest price meeting the user's requirements and budget.

## How to Execute

Run the shopping agent CLI from the repository root:

```bash
uv run shopping-agent search "<ユーザーの指示または商品名>" --format markdown
```

### Useful CLI Flags

- `--format markdown` / `-f markdown`: Outputs clean Markdown tables with product links, prices, and shop rankings.
- `--format json` / `-f json`: Outputs structured JSON for automated filtering.
- `--limit <N>` / `-n <N>`: Limits the number of candidate items (default: 5).
- `--details <N>` / `-d <N>`: Number of top items to fetch individual shop offers for (default: 3).
- `--budget-max <JPY>` / `-b <JPY>`: Explicit maximum budget in Yen (e.g. `150000`).
- `--budget-min <JPY>`: Explicit minimum budget in Yen.
- `--no-llm`: Runs in pure rule-based parsing mode (no API keys required).

### Single Product Direct Compare

To compare all shops for a specific product page:

```bash
uv run shopping-agent compare "<item_url>"
```

## Recommended Workflow for the Agent

1. **Run the search command** with the user's natural instruction:
   ```bash
   uv run shopping-agent search "ノイズキャンセリング ワイヤレスイヤホン 1万円台" -f markdown
   ```
2. **Review the output**:
   - Inspect the top-ranked products and their specifications.
   - Check the shop comparison table for total price (including shipping) and stock status.
3. **Present recommendations to the user**:
   - State the #1 lowest price item and the store selling it.
   - Highlight whether shipping is free and if it is in stock.
   - Provide clickable links to the store/product page.
   - Mention runner-up options or differences in specs if helpful.
