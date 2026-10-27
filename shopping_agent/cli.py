"""CLI entrypoint for shopping agent."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from shopping_agent.agent import ShoppingAgent
from shopping_agent.formatters import format_as_json, format_as_markdown, format_as_rich
from shopping_agent.scrapers.kakaku import KakakuScraper

app = typer.Typer(
    name="shopping-agent",
    help="AI-assisted shopping agent to find and compare lowest prices across stores.",
    add_completion=False,
)
console = Console()


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search instruction or product query, e.g. 'M3 MacBook Air 16GB 15万円以下'"),
    budget_max: Optional[int] = typer.Option(None, "--budget-max", "-b", help="Maximum budget in JPY"),
    budget_min: Optional[int] = typer.Option(None, "--budget-min", help="Minimum budget in JPY"),
    limit: int = typer.Option(5, "--limit", "-n", help="Max number of candidate products to return"),
    details_count: int = typer.Option(3, "--details", "-d", help="Number of top products to fetch shop offers for"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, markdown, or json"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="File path to save the output"),
    use_llm: bool = typer.Option(True, "--llm/--no-llm", help="Whether to use LLM for instruction parsing"),
):
    """Search products, compare prices, and list the best deals."""
    with console.status("[bold green]商品を探索し、各ショップの最安値を比較中...[/bold green]"):
        scraper = KakakuScraper()
        agent = ShoppingAgent(scraper=scraper, use_llm=use_llm)
        try:
            result = agent.search_and_rank(
                instruction=query,
                limit=limit,
                fetch_details_count=details_count,
            )
            # Override budgets if explicitly given via CLI options
            if budget_max is not None:
                result.requirement.budget_max = budget_max
                result.items = [i for i in result.items if i.min_price <= budget_max]
            if budget_min is not None:
                result.requirement.budget_min = budget_min
                result.items = [i for i in result.items if i.min_price >= budget_min]

        finally:
            agent.close()

    if output_format == "json":
        output_text = format_as_json(result)
        if output_file:
            output_file.write_text(output_text, encoding="utf-8")
            console.print(f"[green]JSON結果を保存しました:[/green] {output_file}")
        else:
            print(output_text)
    elif output_format == "markdown":
        output_text = format_as_markdown(result)
        if output_file:
            output_file.write_text(output_text, encoding="utf-8")
            console.print(f"[green]Markdownレポートを保存しました:[/green] {output_file}")
        else:
            print(output_text)
    else:
        format_as_rich(result, console=console)
        if output_file:
            # save markdown representation if output file is specified with table format
            output_file.write_text(format_as_markdown(result), encoding="utf-8")
            console.print(f"\n[green]レポートを保存しました:[/green] {output_file}")


@app.command("compare")
def compare(
    item_url: str = typer.Argument(..., help="Kakaku item detail URL, e.g. 'https://kakaku.com/item/J0000047497/'"),
    limit: int = typer.Option(15, "--limit", "-n", help="Max number of shop offers to display"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, markdown, or json"),
):
    """Compare all retail shop offers for a specific product URL."""
    scraper = KakakuScraper()
    try:
        with console.status("[bold green]ショップ別価格・送料・在庫を取得中...[/bold green]"):
            offers = scraper.fetch_shop_offers(item_url, limit=limit)
    finally:
        scraper.close()

    if not offers:
        console.print("[yellow]ショップ情報が取得できませんでした。[/yellow]")
        return

    if output_format == "json":
        import json
        print(json.dumps([o.model_dump() for o in offers], ensure_ascii=False, indent=2))
        return

    from rich.table import Table
    table = Table(title=f"🏪 ショップ別価格一覧（全 {len(offers)} 件）", show_header=True, header_style="bold cyan")
    table.add_column("順位", justify="center", style="dim", width=4)
    table.add_column("ショップ名", style="bold")
    table.add_column("本体価格", justify="right")
    table.add_column("送料", justify="center")
    table.add_column("総額（税込）", justify="right", style="bold green")
    table.add_column("在庫状況", justify="center")
    table.add_column("備考")

    sorted_offers = sorted(offers, key=lambda x: x.total_price)
    for idx, off in enumerate(sorted_offers, start=1):
        table.add_row(
            str(idx),
            off.shop_name,
            f"¥{off.price:,}",
            off.shipping,
            f"¥{off.total_price:,}",
            off.stock,
            off.comment[:30] if off.comment else "-",
        )

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
