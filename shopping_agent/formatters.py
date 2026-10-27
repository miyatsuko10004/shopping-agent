"""Formatters for displaying and exporting shopping agent results."""

import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from shopping_agent.models import SearchResult


def format_as_rich(result: SearchResult, console: Console | None = None) -> None:
    """Print formatted search results using Rich tables."""
    console = console or Console()

    req = result.requirement
    req_desc = f"[bold cyan]指示:[/bold cyan] {result.query}\n"
    req_desc += f"[bold cyan]検索キーワード:[/bold cyan] {', '.join(req.search_keywords)}"
    if req.budget_max:
        req_desc += f" | [bold green]上限予算:[/bold green] ¥{req.budget_max:,}"
    if req.budget_min:
        req_desc += f" | [bold green]下限予算:[/bold green] ¥{req.budget_min:,}"
    if req.required_specs:
        req_desc += f" | [bold yellow]必須条件:[/bold yellow] {req.required_specs}"

    console.print(Panel(req_desc, title="🛒 ショッピング探索エージェント 結果", border_style="bright_blue"))

    if not result.items:
        console.print("[yellow]該当する商品が見つかりませんでした。条件を緩和して再検索してください。[/yellow]")
        return

    table = Table(title=f"🏆 最安値商品ランキング（該当: {len(result.items)} 件）", show_header=True, header_style="bold magenta")
    table.add_column("順位", justify="center", style="dim", width=4)
    table.add_column("商品名", style="bold")
    table.add_column("最安価格", justify="right", style="bold green")
    table.add_column("評価", justify="center", width=8)
    table.add_column("取扱数", justify="center", width=8)
    table.add_column("主なスペック", style="cyan")

    for idx, item in enumerate(result.items, start=1):
        rating_str = f"★{item.rating:.2f}" if item.rating else "-"
        specs_str = ", ".join([f"{k}:{v}" for k, v in list(item.specs.items())[:3]])

        table.add_row(
            str(idx),
            item.name,
            f"¥{item.min_price:,}",
            rating_str,
            f"{item.shop_count}店",
            specs_str or "-",
        )

    console.print(table)

    # Detailed shop offers for top products
    has_offers = any(item.offers for item in result.items)
    if has_offers:
        console.print("\n[bold yellow]🏪 上位商品のショップ別価格・在庫詳細:[/bold yellow]")
        for idx, item in enumerate(result.items, start=1):
            if not item.offers:
                continue

            shop_table = Table(title=f"#{idx} {item.name[:50]}...", show_header=True, header_style="bold cyan")
            shop_table.add_column("ショップ名", style="bold")
            shop_table.add_column("本体価格", justify="right")
            shop_table.add_column("送料", justify="center")
            shop_table.add_column("総額", justify="right", style="bold green")
            shop_table.add_column("在庫状況", justify="center")
            shop_table.add_column("決済/備考")

            for offer in item.offers:
                pay_str = ", ".join(offer.payment_methods[:2])
                extra = f"[{pay_str}] {offer.comment[:25]}" if offer.comment else pay_str
                shop_table.add_row(
                    offer.shop_name,
                    f"¥{offer.price:,}",
                    offer.shipping,
                    f"¥{offer.total_price:,}",
                    offer.stock,
                    extra or "-",
                )
            console.print(shop_table)


def format_as_markdown(result: SearchResult) -> str:
    """Generate Markdown report for agents or documentation."""
    req = result.requirement
    lines: list[str] = []
    lines.append(f"# 🛒 ショッピング探索レポート: {result.query}")
    lines.append("")
    lines.append(f"- **検索キーワード:** {', '.join(req.search_keywords)}")
    if req.budget_max:
        lines.append(f"- **上限予算:** ¥{req.budget_max:,}")
    if req.budget_min:
        lines.append(f"- **下限予算:** ¥{req.budget_min:,}")
    if req.required_specs:
        specs_desc = ", ".join([f"{k}: {v}" for k, v in req.required_specs.items()])
        lines.append(f"- **指定スペック要件:** {specs_desc}")
    lines.append(f"- **該当商品数:** {len(result.items)} 件")
    lines.append("")

    if not result.items:
        lines.append("> 該当する商品が見つかりませんでした。")
        return "\n".join(lines)

    lines.append("## 🏆 最安値商品一覧")
    lines.append("")
    lines.append("| 順位 | 商品名 | 最安価格 | 評価 | 取扱店舗 | 主要スペック | 詳細リンク |")
    lines.append("| :---: | :--- | :---: | :---: | :---: | :--- | :---: |")

    for idx, item in enumerate(result.items, start=1):
        rating_str = f"★{item.rating:.2f}" if item.rating else "-"
        specs_str = "<br>".join([f"**{k}**: {v}" for k, v in list(item.specs.items())[:3]])
        lines.append(
            f"| {idx} | [{item.name}]({item.detail_url}) | **¥{item.min_price:,}** | {rating_str} | {item.shop_count}店 | {specs_str or '-'} | [価格比較]({item.detail_url}) |"
        )

    lines.append("")

    # Detail offers
    for idx, item in enumerate(result.items, start=1):
        if not item.offers:
            continue
        lines.append(f"### #{idx} [{item.name}]({item.detail_url}) ショップ別価格")
        lines.append("")
        lines.append("| ショップ名 | 本体価格 | 送料 | 総額（税込） | 在庫 | 備考・売り場リンク |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :--- |")

        for off in item.offers:
            link_md = f"[{off.shop_name} 売り場へ]({off.product_url})"
            lines.append(
                f"| {off.shop_name} | ¥{off.price:,} | {off.shipping} | **¥{off.total_price:,}** | {off.stock} | {link_md} |"
            )
        lines.append("")

    return "\n".join(lines)


def format_as_json(result: SearchResult) -> str:
    """Serialize to JSON string."""
    return result.model_dump_json(indent=2)
