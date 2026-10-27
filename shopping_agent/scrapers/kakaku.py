"""Kakaku.com scraper implementation."""

import re
import urllib.parse
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from shopping_agent.models import ProductItem, ShopOffer
from shopping_agent.scrapers.base import BaseScraper


def _parse_price(text: str) -> Optional[int]:
    """Extract integer price from string (e.g. '¥171,066〜' -> 171066)."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", text)
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            return None
    return None


def _parse_shipping_fee(text: str) -> int:
    """Extract shipping fee from text. Returns 0 if free/included."""
    if not text:
        return 0
    if "無料" in text or "込" in text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    if digits:
        try:
            return int(digits)
        except ValueError:
            return 0
    return 0


class KakakuScraper(BaseScraper):
    """Scraper for kakaku.com search and shop comparison."""

    BASE_URL = "https://kakaku.com"
    SEARCH_URL = "https://kakaku.com/search_results/{query}/"

    def __init__(self, timeout: float = 15.0):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        }
        self.client = httpx.Client(
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True,
        )

    def _decode_response(self, response: httpx.Response) -> str:
        """Properly decode Japanese encodings (cp932/shift_jis/utf-8)."""
        content_type = response.headers.get("content-type", "").lower()
        if "shift" in content_type or "sjis" in content_type or "cp932" in content_type:
            return response.content.decode("cp932", errors="replace")

        # Try utf-8 first
        try:
            return response.content.decode("utf-8")
        except UnicodeDecodeError:
            return response.content.decode("cp932", errors="replace")

    def search(self, query: str, limit: int = 20) -> list[ProductItem]:
        """Search products on kakaku.com."""
        encoded_query = urllib.parse.quote(query.strip().encode("cp932", errors="replace"))
        url = self.SEARCH_URL.format(query=encoded_query)

        try:
            resp = self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            return []

        html = self._decode_response(resp)
        soup = BeautifulSoup(html, "lxml")

        items: list[ProductItem] = []
        raw_items = soup.select(".item, .p-result_item, .p-item, .hitItem")

        for item_el in raw_items:
            if len(items) >= limit:
                break

            # Product Name & Link
            name_el = item_el.select_one(".s-targetLink, .itemname a, .p-item_name a, .title a, a.title")
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            href = name_el.get("href", "")
            if href.startswith("/"):
                detail_url = urllib.parse.urljoin(self.BASE_URL, href)
            else:
                detail_url = href

            # Price
            price_el = item_el.select_one(".p-item_priceNum, .price, .p-item_price, .pricerange")
            min_price = _parse_price(price_el.get_text() if price_el else "")
            if min_price is None:
                continue

            # Maker
            maker_el = item_el.select_one(".p-item_maker, .maker")
            maker = maker_el.get_text(strip=True) if maker_el else ""

            # Category
            cat_el = item_el.select_one(".p-item_category, .category")
            category = cat_el.get_text(strip=True) if cat_el else ""

            # Rating & Review Count
            rating_el = item_el.select_one(".p-item_star_rating_num, .rating")
            rating = None
            if rating_el:
                try:
                    rating = float(rating_el.get_text(strip=True))
                except ValueError:
                    rating = None

            voice_el = item_el.select_one(".p-item_voice_num, .voice")
            review_count = 0
            if voice_el:
                r_num = _parse_price(voice_el.get_text())
                if r_num:
                    review_count = r_num

            # Release date
            date_el = item_el.select_one(".p-item_date")
            release_date = date_el.get_text(strip=True) if date_el else ""

            # Specifications
            specs: dict[str, str] = {}
            spec_ttls = item_el.select(".p-item_spec_ttl")
            spec_datas = item_el.select(".p-item_spec_data")
            for ttl, data in zip(spec_ttls, spec_datas):
                t_txt = ttl.get_text(strip=True)
                d_txt = data.get_text(strip=True)
                if t_txt and d_txt:
                    specs[t_txt] = d_txt

            # Shop count
            shop_count_el = item_el.select_one(".p-item_shopCounts_num")
            shop_count = 0
            if shop_count_el:
                s_num = _parse_price(shop_count_el.get_text())
                if s_num:
                    shop_count = s_num

            product = ProductItem(
                name=name,
                maker=maker,
                category=category,
                min_price=min_price,
                rating=rating,
                review_count=review_count,
                release_date=release_date,
                specs=specs,
                shop_count=shop_count,
                detail_url=detail_url,
            )
            items.append(product)

        return items

    def fetch_shop_offers(self, item_url: str, limit: int = 15) -> list[ShopOffer]:
        """Fetch shop offers and prices from the product detail page."""
        try:
            resp = self.client.get(item_url)
            resp.raise_for_status()
        except httpx.HTTPError:
            return []

        html = self._decode_response(resp)
        soup = BeautifulSoup(html, "lxml")

        offers: list[ShopOffer] = []
        shop_items = soup.select(".p-priceList_item")

        for s_el in shop_items:
            if len(offers) >= limit:
                break

            # Price
            price_el = s_el.select_one(".p-priceList_price, .price")
            price = _parse_price(price_el.get_text() if price_el else "")
            if price is None:
                continue

            # Shop Name
            name_el = s_el.select_one(
                ".p-priceList_shopName, .p-priceList_shopNameWrap, h3, .shopName, .p-shop_name, .p-shopTable_shopName"
            )
            shop_name = name_el.get_text(strip=True) if name_el else "不明ショップ"
            shop_name = re.sub(r"カートに入れる.*|売り場へ行く.*", "", shop_name).strip()

            # Shipping & Stock info (kakaku lists them under .p-priceList_txt)
            txt_els = [el.get_text(strip=True) for el in s_el.select(".p-priceList_txt")]
            shipping_desc = "無料"
            stock_desc = "在庫あり"

            for txt in txt_els:
                if "無料" in txt or "送料" in txt or "円" in txt:
                    shipping_desc = txt
                elif "在庫" in txt or "入荷" in txt or "出荷" in txt or "営業日" in txt:
                    stock_desc = txt

            shipping_fee = _parse_shipping_fee(shipping_desc)
            total_price = price + shipping_fee

            # Comment / Note
            comment_el = s_el.select_one(".p-priceList_shopComment")
            comment = comment_el.get_text(strip=True) if comment_el else ""

            # Payment methods
            pay_labels = [el.get_text(strip=True) for el in s_el.select(".p-priceList_paylabel")]

            # Link (Direct store forwarder link or kakaku shop link)
            btn_el = s_el.select_one("a.p-shopBtn, a.s-linkBigger_href, a[href*='forwarder'], a[href*='forward.aspx']")
            if not btn_el:
                btn_el = s_el.find("a", href=True)

            if btn_el and btn_el.get("href"):
                href = btn_el["href"]
                product_url = urllib.parse.urljoin(self.BASE_URL, href)
            else:
                product_url = item_url

            offers.append(
                ShopOffer(
                    shop_name=shop_name,
                    price=price,
                    shipping=shipping_desc,
                    shipping_fee=shipping_fee,
                    total_price=total_price,
                    stock=stock_desc,
                    comment=comment,
                    payment_methods=pay_labels,
                    product_url=product_url,
                )
            )

        return offers

    def close(self):
        self.client.close()
