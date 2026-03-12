"""Rich CLI display for BENZEMA216 Council council reports."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import CouncilReport, Verdict

console = Console()

VERDICT_STYLE = {
    Verdict.STRONG_BUY: ("STRONG BUY", "bold green"),
    Verdict.BUY: ("BUY", "green"),
    Verdict.NEUTRAL: ("NEUTRAL", "yellow"),
    Verdict.REDUCE: ("REDUCE", "dark_orange"),
    Verdict.SELL: ("SELL", "bold red"),
}


def display_report(report: CouncilReport) -> None:
    """Display a full council report with rich formatting."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]BENZEMA216 COUNCIL[/] — Swarm Intelligence Investment Council",
            style="cyan",
        )
    )
    console.print()

    # ── 1. Consensus Summary ──
    _display_consensus(report)

    # ── 2. Individual Master Opinions ──
    _display_opinions(report)

    # ── 3. Dissent & Notable Views ──
    _display_dissent(report)

    console.print()


def _display_consensus(report: CouncilReport) -> None:
    """Display the consensus table."""
    if not report.consensus:
        return

    console.print("[bold]Consensus Summary[/]")
    console.print()

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Trade", style="bold", width=20)
    table.add_column("B216 Score", justify="center", width=15)
    table.add_column("Consensus", justify="center", width=18)
    table.add_column("Bull / Bear / Neutral", justify="center", width=20)
    table.add_column("Top Bull Reason", width=40)

    for ci in report.consensus:
        # Score color
        if ci.b216_score > 0.3:
            score_style = "bold green"
        elif ci.b216_score < -0.3:
            score_style = "bold red"
        else:
            score_style = "yellow"

        # Consensus level style
        level_map = {
            "strong_consensus": ("Strong", "bold green"),
            "moderate_consensus": ("Moderate", "yellow"),
            "divided": ("Divided", "bold red"),
        }
        level_text, level_style = level_map.get(
            ci.consensus_level, ("?", "white")
        )

        table.add_row(
            f"{ci.action.upper()} {ci.ticker}",
            Text(f"{ci.b216_score:+.2f}", style=score_style),
            Text(level_text, style=level_style),
            f"{ci.bull_count} / {ci.bear_count} / {ci.neutral_count}",
            ci.top_bull_reason[:80] + ("..." if len(ci.top_bull_reason) > 80 else ""),
        )

    console.print(table)
    console.print()


def _display_opinions(report: CouncilReport) -> None:
    """Display individual master opinions as a vote matrix."""
    if not report.opinions:
        return

    # Collect all tickers from trade reviews
    all_tickers: list[str] = []
    for op in report.opinions:
        for tr in op.trade_reviews:
            key = f"{tr.action.upper()} {tr.ticker}"
            if key not in all_tickers:
                all_tickers.append(key)

    if not all_tickers:
        return

    console.print("[bold]Master Vote Matrix[/]")
    console.print()

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Master", style="bold", width=22)
    table.add_column("School", width=12)

    for ticker_key in all_tickers:
        table.add_column(ticker_key, justify="center", width=14)

    for op in report.opinions:
        row = [f"{op.master_name_cn}", op.school]

        for ticker_key in all_tickers:
            # Find matching review
            found = False
            for tr in op.trade_reviews:
                key = f"{tr.action.upper()} {tr.ticker}"
                if key == ticker_key:
                    label, style = VERDICT_STYLE.get(
                        tr.verdict, ("?", "white")
                    )
                    row.append(Text(f"{label}\n({tr.confidence}%)", style=style))
                    found = True
                    break
            if not found:
                row.append(Text("—", style="dim"))

        table.add_row(*row)

    console.print(table)
    console.print()


def _display_dissent(report: CouncilReport) -> None:
    """Display notable dissenting views."""
    if not report.consensus:
        return

    console.print("[bold]Notable Dissent & Insights[/]")
    console.print()

    for ci in report.consensus:
        if ci.consensus_level == "divided" or ci.notable_dissent != "观点均匀分布，无明显异议":
            console.print(
                Panel(
                    f"[bold]{ci.action.upper()} {ci.ticker}[/] (Score: {ci.b216_score:+.2f})\n\n"
                    f"[green]Top Bull:[/] {ci.top_bull_reason[:200]}\n\n"
                    f"[red]Top Bear:[/] {ci.top_bear_reason[:200]}\n\n"
                    f"[yellow]Dissent:[/] {ci.notable_dissent[:200]}",
                    title=f"{'Divided' if ci.consensus_level == 'divided' else 'Notable Dissent'}",
                    border_style="yellow",
                )
            )


def display_master_detail(report: CouncilReport, master_id: str) -> None:
    """Display detailed opinion from a specific master."""
    for op in report.opinions:
        if op.master_id == master_id:
            console.print()
            console.print(
                Panel(
                    f"[bold]{op.master_name}[/] ({op.master_name_cn}) — {op.school}",
                    style="cyan",
                )
            )
            console.print(f"\n[bold]Portfolio Assessment:[/]\n{op.portfolio_assessment}\n")

            for tr in op.trade_reviews:
                label, style = VERDICT_STYLE.get(tr.verdict, ("?", "white"))
                console.print(
                    f"  [{style}]{label}[/] {tr.action.upper()} {tr.ticker} "
                    f"(confidence: {tr.confidence}%)"
                )
                console.print(f"    {tr.reasoning}\n")

            if op.key_advice:
                console.print(f"[bold]Key Advice:[/] {op.key_advice}\n")
            return

    console.print(f"[red]Master '{master_id}' not found in report.[/]")
