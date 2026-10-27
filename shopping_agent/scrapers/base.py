"""Base scraper interface."""

from abc import ABC, abstractmethod
from shopping_agent.models import ProductItem, ShopOffer


class BaseScraper(ABC):
    """Abstract base class for shopping scrapers."""

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[ProductItem]:
        """Search products matching the query."""
        pass

    @abstractmethod
    def fetch_shop_offers(self, item_url: str, limit: int = 10) -> list[ShopOffer]:
        """Fetch individual shop prices and stock for a product."""
        pass
