"""Shopping agent core logic."""

import json
import os
import re
from typing import Optional
import httpx

from shopping_agent.models import (
    ProductItem,
    SearchRequirement,
    SearchResult,
    ShopOffer,
)
from shopping_agent.scrapers.kakaku import KakakuScraper


class ShoppingAgent:
    """Agent that plans search queries, filters products, and compares prices."""

    def __init__(self, scraper: Optional[KakakuScraper] = None, use_llm: bool = True):
        self.scraper = scraper or KakakuScraper()
        self.use_llm = use_llm
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def parse_instruction(self, instruction: str) -> SearchRequirement:
        """Parse natural language instruction into structured requirements."""
        if self.use_llm and (self.gemini_api_key or self.openai_api_key):
            try:
                if self.gemini_api_key:
                    return self._parse_with_gemini(instruction)
                elif self.openai_api_key:
                    return self._parse_with_openai(instruction)
            except Exception:
                # Fallback to heuristic parser if LLM call fails
                pass

        return self._parse_heuristic(instruction)

    def _parse_heuristic(self, instruction: str) -> SearchRequirement:
        """Heuristic rule-based requirement extraction."""
        text = instruction.strip()

        # Extract "X万円台" or "X万台" (e.g. 1万円台 -> 10000..20000)
        dai_match = re.search(r"(\d+)\s*(?:万|万円)台", text)
        budget_min = None
        budget_max = None
        if dai_match:
            base_man = int(dai_match.group(1))
            budget_min = base_man * 10000
            budget_max = (base_man + 1) * 10000
        else:
            # Extract budget max
            # e.g. "15万円以下", "15万以内", "15万以下", "150,000円以下", "予算15万"
            man_max = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|万円)\s*(?:以下|以内|未満|まで|程度)?", text)
            if man_max:
                try:
                    budget_max = int(float(man_max.group(1)) * 10000)
                except ValueError:
                    pass
            else:
                yen_max = re.search(r"(\d{1,3}(?:,\d{3})+|\d{4,9})\s*円\s*(?:以下|以内|未満|まで)?", text)
                if yen_max:
                    try:
                        budget_max = int(yen_max.group(1).replace(",", ""))
                    except ValueError:
                        pass

            # Extract budget min (e.g. "10万円以上")
            min_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|万円)\s*以上", text)
            if min_match:
                try:
                    budget_min = int(float(min_match.group(1)) * 10000)
                except ValueError:
                    pass

        # Extract memory/RAM specs (only if explicitly prefixed with メモリ or RAM)
        required_specs: dict[str, str] = {}
        ram_match = re.search(r"(?:メモリ|RAM)\s*[:：]?\s*(\d+GB)", text, re.I)
        if ram_match:
            required_specs["メモリ"] = ram_match.group(1).upper()

        # Extract storage specs (only if explicitly prefixed with SSD or ストレージ)
        storage_match = re.search(r"(?:SSD|ストレージ)\s*[:：]?\s*(\d+(?:GB|TB))", text, re.I)
        if storage_match:
            required_specs["ストレージ"] = storage_match.group(1).upper()

        # Clean search keywords
        cleaned = text
        # Remove budget and range phrases
        cleaned = re.sub(r"\d+\s*(?:万|万円)?台", " ", cleaned)
        cleaned = re.sub(r"\d+(?:\.\d+)?\s*(?:万|万円|円)\s*(?:以下|以内|未満|まで|以上|程度)?", " ", cleaned)
        cleaned = re.sub(r"予算\s*\d+(?:\.\d+)?\s*(?:万|万円|円)?", " ", cleaned)
        # Remove common agent query phrases
        cleaned = re.sub(r"(?:で|の)?最安値(?:のもの|のリスト|を探して|を教えて|ランキング|一覧)?", " ", cleaned)
        cleaned = re.sub(r"(?:おすすめ|要件を満たす|見つけてくる|ほしい|探して|比較して|検索して|教えて)", " ", cleaned)
        cleaned = re.sub(r"(?:円以下|万円以下|円以内|万以内|以下|以内|未満|以上|程度|円台|台)", " ", cleaned)
        cleaned = re.sub(r"[\s,、]+", " ", cleaned).strip()

        stopwords = {"円", "万", "円台", "台", "円以下", "万円以下", "以下", "以内", "未満", "以上", "程度", "予算", "最安値", "最安", "おすすめ"}
        keywords = [k for k in cleaned.split(" ") if k and k not in stopwords]
        if not keywords:
            keywords = [instruction]

        return SearchRequirement(
            raw_query=instruction,
            search_keywords=keywords,
            budget_min=budget_min,
            budget_max=budget_max,
            required_specs=required_specs,
        )


    def _parse_with_gemini(self, instruction: str) -> SearchRequirement:
        """Parse with Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
        prompt = f"""
You are an e-commerce shopping agent assistant.
Analyze the following user instruction and extract search parameters into a JSON object.

User instruction: "{instruction}"

Output strictly JSON with this structure:
{{
  "search_keywords": ["keyword1", "keyword2"],
  "budget_min": null or integer (in JPY),
  "budget_max": null or integer (in JPY),
  "required_specs": {{"spec_name": "spec_value"}},
  "negative_keywords": []
}}
Note: search_keywords should be concise product search query (e.g. ["MacBook Air", "M3"]).
Do not include explanation or markdown codeblocks outside JSON.
"""
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # remove ```json ``` if present
            content = re.sub(r"^```(?:json)?\n", "", content)
            content = re.sub(r"\n```$", "", content)
            parsed = json.loads(content)

            return SearchRequirement(
                raw_query=instruction,
                search_keywords=parsed.get("search_keywords", [instruction]),
                budget_min=parsed.get("budget_min"),
                budget_max=parsed.get("budget_max"),
                required_specs=parsed.get("required_specs", {}),
                negative_keywords=parsed.get("negative_keywords", []),
            )

    def _parse_with_openai(self, instruction: str) -> SearchRequirement:
        """Parse with OpenAI compatible API."""
        url = f"{self.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        prompt = f"""
Analyze the user instruction and extract search parameters into JSON.
Instruction: "{instruction}"
Output JSON schema:
{{
  "search_keywords": ["string"],
  "budget_min": null or integer in JPY,
  "budget_max": null or integer in JPY,
  "required_specs": {{"spec_name": "spec_value"}},
  "negative_keywords": ["string"]
}}
"""
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            parsed = json.loads(data["choices"][0]["message"]["content"])

            return SearchRequirement(
                raw_query=instruction,
                search_keywords=parsed.get("search_keywords", [instruction]),
                budget_min=parsed.get("budget_min"),
                budget_max=parsed.get("budget_max"),
                required_specs=parsed.get("required_specs", {}),
                negative_keywords=parsed.get("negative_keywords", []),
            )

    def search_and_rank(
        self,
        instruction: str,
        limit: int = 10,
        fetch_details_count: int = 3,
        strict_budget: bool = True,
    ) -> SearchResult:
        """Execute search, apply filters, and fetch detailed shop prices for top products."""
        requirement = self.parse_instruction(instruction)

        # Build search query string
        search_query = " ".join(requirement.search_keywords)

        # Scrape candidates
        raw_items = self.scraper.search(search_query, limit=max(limit * 5, 40))

        # Filter items according to requirement
        filtered_items: list[ProductItem] = []
        for item in raw_items:
            # Budget check
            if requirement.budget_max is not None and strict_budget:
                if item.min_price > requirement.budget_max:
                    continue
            if requirement.budget_min is not None and strict_budget:
                if item.min_price < requirement.budget_min:
                    continue

            # Spec / keyword check
            matched_specs = True
            for req_key, req_val in requirement.required_specs.items():
                val_str = str(req_val).lower()
                # Check either in product specs or in product name
                found_in_specs = any(val_str in str(v).lower() for v in item.specs.values())
                found_in_name = val_str in item.name.lower()
                if not (found_in_specs or found_in_name):
                    matched_specs = False
                    break

            if not matched_specs:
                continue

            # Negative keywords check
            has_negative = any(neg.lower() in item.name.lower() for neg in requirement.negative_keywords)
            if has_negative:
                continue

            filtered_items.append(item)

        # If strict filtering eliminated all results, fallback to raw items with warning
        if not filtered_items and raw_items:
            filtered_items = raw_items[:limit]

        # Sort by minimum price ascending
        filtered_items.sort(key=lambda x: x.min_price)
        top_items = filtered_items[:limit]

        # Fetch shop details for top N items
        for i, item in enumerate(top_items[:fetch_details_count]):
            offers = self.scraper.fetch_shop_offers(item.detail_url, limit=10)
            item.offers = offers
            if offers:
                # Update with actual total price if shipping fee included
                sorted_offers = sorted(offers, key=lambda o: o.total_price)
                item.offers = sorted_offers

        return SearchResult(
            query=instruction,
            requirement=requirement,
            total_found=len(top_items),
            items=top_items,
        )

    def close(self):
        self.scraper.close()
