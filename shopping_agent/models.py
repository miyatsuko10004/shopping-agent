"""Data models for shopping agent."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ShopOffer(BaseModel):
    """Specific shop offering for a product."""
    shop_name: str = Field(description="Name of the retail shop")
    price: int = Field(description="Price in JPY (tax included)")
    shipping: str = Field(default="無料", description="Shipping fee description")
    shipping_fee: int = Field(default=0, description="Parsed shipping fee in JPY (0 if free/included)")
    total_price: int = Field(description="Total price including shipping in JPY")
    stock: str = Field(default="在庫あり", description="Stock availability status")
    comment: str = Field(default="", description="Shop comment or condition notice")
    payment_methods: list[str] = Field(default_factory=list, description="Supported payment methods")
    product_url: str = Field(description="Direct shop landing or redirect URL")


class ProductItem(BaseModel):
    """Product model containing specifications and offers."""
    name: str = Field(description="Full product title")
    maker: str = Field(default="", description="Manufacturer or brand")
    category: str = Field(default="", description="Product category")
    min_price: int = Field(description="Lowest available price in JPY")
    max_price: Optional[int] = Field(default=None, description="Highest available price in JPY")
    rating: Optional[float] = Field(default=None, description="Average review rating (0.0 - 5.0)")
    review_count: int = Field(default=0, description="Total number of reviews/ratings")
    release_date: str = Field(default="", description="Release date if available")
    specs: dict[str, str] = Field(default_factory=dict, description="Key-value specifications (CPU, RAM, etc.)")
    shop_count: int = Field(default=0, description="Total number of shops selling this item")
    detail_url: str = Field(description="Kakaku.com detail page URL")
    offers: list[ShopOffer] = Field(default_factory=list, description="Detailed list of shop offers")


class SearchRequirement(BaseModel):
    """Parsed user search requirement."""
    raw_query: str = Field(description="Original user instruction")
    search_keywords: list[str] = Field(default_factory=list, description="Keywords to pass to search engine")
    budget_min: Optional[int] = Field(default=None, description="Minimum price in JPY")
    budget_max: Optional[int] = Field(default=None, description="Maximum price in JPY")
    required_specs: dict[str, Any] = Field(default_factory=dict, description="Required specs, e.g. {'メモリ': '16GB'}")
    negative_keywords: list[str] = Field(default_factory=list, description="Keywords to exclude")
    sort_by: str = Field(default="price_asc", description="Sort order: price_asc, rating_desc, popular")


class SearchResult(BaseModel):
    """Final output result."""
    query: str
    requirement: SearchRequirement
    total_found: int
    items: list[ProductItem]
