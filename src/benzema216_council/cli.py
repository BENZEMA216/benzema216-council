"""CLI entry point for BENZEMA216 Council."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .display import display_master_detail, display_report
from .engine import DEFAULT_MODEL, run_council
from .masters import MASTERS, get_all_master_ids
from .models import Portfolio, Position, ProposedTrade

console = Console()


def load_portfolio(path: str) -> Portfolio:
    """Load portfolio from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    positions = [Position(**p) for p in data.get("positions", [])]
    trades = [ProposedTrade(**t) for t in data.get("proposed_trades", [])]

    return Portfolio(
        cash=data.get("cash", 0),
        positions=positions,
        proposed_trades=trades,
        context=data.get("context", ""),
    )


async def _run(args: argparse.Namespace) -> None:
    """Async main runner."""
    # Load portfolio
    portfolio = load_portfolio(args.portfolio)

    console.print(f"\n[bold cyan]BENZEMA216 Council[/] v0.1.0")
    console.print(f"Portfolio: {len(portfolio.positions)} positions, ${portfolio.cash:,.0f} cash")
    console.print(f"Proposed trades: {len(portfolio.proposed_trades)}")

    # Select masters
    master_ids = None
    if args.masters:
        master_ids = [m.strip() for m in args.masters.split(",")]
        console.print(f"Masters: {len(master_ids)} selected")
    elif args.region:
        master_ids = [m["id"] for m in MASTERS if m["region"] == args.region]
        console.print(f"Masters: {len(master_ids)} ({args.region} only)")
    else:
        console.print(f"Masters: all {len(MASTERS)} (use --region or --masters to filter)")

    model = args.model or DEFAULT_MODEL
    console.print(f"Model: {model}\n")

    # Run council with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        n = len(master_ids) if master_ids else len(MASTERS)
        task = progress.add_task(
            f"Consulting {n} investment masters...", total=None
        )

        start = time.time()
        report = await run_council(
            portfolio=portfolio,
            master_ids=master_ids,
            model=model,
            max_concurrent=args.concurrency,
        )
        elapsed = time.time() - start

        progress.update(task, completed=True)

    console.print(f"[dim]Council completed in {elapsed:.1f}s[/]\n")

    # Display report
    display_report(report)

    # Detail view for specific master
    if args.detail:
        display_master_detail(report, args.detail)

    # Save raw JSON if requested
    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
        console.print(f"[dim]Raw report saved to {args.output}[/]")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BENZEMA216 Council — Swarm Intelligence Investment Council",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  b216 portfolio.yaml
  b216 portfolio.yaml --region cn
  b216 portfolio.yaml --masters warren_buffett,li_lu,peter_lynch
  b216 portfolio.yaml --detail warren_buffett
  b216 portfolio.yaml --output report.json
        """,
    )
    parser.add_argument("portfolio", nargs="?", help="Path to portfolio YAML file")
    parser.add_argument(
        "--masters",
        help="Comma-separated list of master IDs to consult",
    )
    parser.add_argument(
        "--region",
        choices=["us", "cn"],
        help="Only consult masters from this region",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"LLM model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Max concurrent API calls (default: 10)",
    )
    parser.add_argument(
        "--detail",
        help="Show detailed opinion from a specific master ID",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save raw JSON report to file",
    )
    parser.add_argument(
        "--list-masters",
        action="store_true",
        help="List all available masters and exit",
    )

    args = parser.parse_args()

    if args.list_masters:
        console.print("\n[bold]Available Masters:[/]\n")
        for m in MASTERS:
            console.print(f"  {m['id']:25s} {m['name_cn']} ({m['name']}) — {m['school']}")
        console.print()
        sys.exit(0)

    if not args.portfolio:
        parser.error("portfolio file is required (unless using --list-masters)")

    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set.[/]")
        console.print("  export ANTHROPIC_API_KEY=sk-ant-xxx")
        sys.exit(1)

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
