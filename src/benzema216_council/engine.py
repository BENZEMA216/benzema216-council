"""Core consultation engine — runs all masters in parallel and aggregates results."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

import anthropic

from .masters import MASTERS
from .models import (
    ConsensusItem,
    CouncilReport,
    MasterOpinion,
    Portfolio,
    TradeReview,
    Verdict,
)

# ─── LLM Client ──────────────────────────────────────────────────────

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _build_portfolio_prompt(portfolio: Portfolio) -> str:
    """Build a human-readable portfolio description for the LLM."""
    lines = ["## Current Portfolio\n"]

    if portfolio.cash > 0:
        lines.append(f"- Cash: ${portfolio.cash:,.2f}")

    if portfolio.positions:
        lines.append("\n### Positions:")
        for p in portfolio.positions:
            lines.append(
                f"- {p.ticker} ({p.market.upper()}): {p.shares} shares @ avg cost ${p.avg_cost:.2f} "
                f"(cost basis: ${p.cost_basis:,.2f})"
            )

    if portfolio.proposed_trades:
        lines.append("\n### Proposed Trades (evaluate these):")
        for t in portfolio.proposed_trades:
            reason_part = f" — Reason: {t.reason}" if t.reason else ""
            lines.append(
                f"- {t.action.upper()} {t.shares} shares of {t.ticker} ({t.market.upper()}){reason_part}"
            )

    if portfolio.context:
        lines.append(f"\n### Additional Context:\n{portfolio.context}")

    return "\n".join(lines)


def _build_system_prompt(master: dict) -> str:
    """Build system prompt for a master agent."""
    return f"""{master["persona"]}

OUTPUT FORMAT:
You must respond with valid JSON matching this exact structure:
{{
  "portfolio_assessment": "Brief overall assessment of the portfolio (2-3 sentences)",
  "trade_reviews": [
    {{
      "ticker": "TICKER",
      "action": "buy/sell/short",
      "verdict": "strong_buy|buy|neutral|reduce|sell",
      "confidence": 0-100,
      "reasoning": "2-3 sentences explaining your reasoning from your investment philosophy"
    }}
  ],
  "key_advice": "One key piece of advice for this investor based on your philosophy (1-2 sentences)"
}}

Review EVERY proposed trade. Be authentic to your investment philosophy — don't just agree with everything.
If you would genuinely have no opinion on a stock (outside your circle of competence), say so honestly.
Respond in Chinese (中文) for the reasoning text."""


async def consult_master(
    client: anthropic.AsyncAnthropic,
    master: dict,
    portfolio: Portfolio,
    model: str = DEFAULT_MODEL,
) -> MasterOpinion:
    """Consult a single investment master about the portfolio."""
    portfolio_prompt = _build_portfolio_prompt(portfolio)

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=2000,
            system=_build_system_prompt(master),
            messages=[
                {
                    "role": "user",
                    "content": f"Please analyze this portfolio and proposed trades:\n\n{portfolio_prompt}",
                }
            ],
        )

        # Parse the JSON response
        raw = response.content[0].text
        # Handle potential markdown code blocks
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]

        data = json.loads(raw)

        trade_reviews = []
        for tr in data.get("trade_reviews", []):
            verdict_str = tr.get("verdict", "neutral").lower().strip()
            # Normalize verdict
            verdict_map = {
                "strong_buy": Verdict.STRONG_BUY,
                "buy": Verdict.BUY,
                "neutral": Verdict.NEUTRAL,
                "reduce": Verdict.REDUCE,
                "sell": Verdict.SELL,
                "approve": Verdict.BUY,
                "reject": Verdict.SELL,
            }
            verdict = verdict_map.get(verdict_str, Verdict.NEUTRAL)

            trade_reviews.append(
                TradeReview(
                    ticker=tr["ticker"],
                    action=tr["action"],
                    verdict=verdict,
                    confidence=min(100, max(0, int(tr.get("confidence", 50)))),
                    reasoning=tr.get("reasoning", ""),
                )
            )

        return MasterOpinion(
            master_id=master["id"],
            master_name=master["name"],
            master_name_cn=master["name_cn"],
            school=master["school"],
            portfolio_assessment=data.get("portfolio_assessment", ""),
            trade_reviews=trade_reviews,
            key_advice=data.get("key_advice", ""),
        )

    except Exception as e:
        # Return a minimal opinion on error
        return MasterOpinion(
            master_id=master["id"],
            master_name=master["name"],
            master_name_cn=master["name_cn"],
            school=master["school"],
            portfolio_assessment=f"[Error consulting {master['name']}: {e}]",
            trade_reviews=[],
            key_advice="",
        )


# ─── Council (Swarm Intelligence) ────────────────────────────────────

VERDICT_SCORES = {
    Verdict.STRONG_BUY: 1.0,
    Verdict.BUY: 0.5,
    Verdict.NEUTRAL: 0.0,
    Verdict.REDUCE: -0.5,
    Verdict.SELL: -1.0,
}


def _aggregate_consensus(
    opinions: list[MasterOpinion], portfolio: Portfolio
) -> list[ConsensusItem]:
    """Aggregate individual master opinions into consensus using weighted voting."""
    consensus = []

    for trade in portfolio.proposed_trades:
        # Collect all reviews for this trade
        reviews: list[tuple[MasterOpinion, TradeReview]] = []
        for opinion in opinions:
            for tr in opinion.trade_reviews:
                if tr.ticker.upper() == trade.ticker.upper():
                    reviews.append((opinion, tr))

        if not reviews:
            continue

        # Weighted score: verdict_score * (confidence / 100)
        weighted_scores = []
        bull_reasons = []
        bear_reasons = []

        bull_count = 0
        bear_count = 0
        neutral_count = 0

        for opinion, tr in reviews:
            score = VERDICT_SCORES[tr.verdict]
            weight = tr.confidence / 100.0
            weighted_scores.append(score * weight)

            if score > 0:
                bull_count += 1
                bull_reasons.append((tr.confidence, tr.reasoning, opinion.master_name_cn))
            elif score < 0:
                bear_count += 1
                bear_reasons.append((tr.confidence, tr.reasoning, opinion.master_name_cn))
            else:
                neutral_count += 1

        # B216 Score: average of weighted scores, clamped to [-1, 1]
        b216_score = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0
        b216_score = max(-1.0, min(1.0, b216_score))

        # Consensus level
        total = bull_count + bear_count + neutral_count
        max_faction = max(bull_count, bear_count, neutral_count)
        if total > 0 and max_faction / total >= 0.7:
            consensus_level = "strong_consensus"
        elif total > 0 and max_faction / total >= 0.5:
            consensus_level = "moderate_consensus"
        else:
            consensus_level = "divided"

        # Top reasons (highest confidence)
        bull_reasons.sort(key=lambda x: x[0], reverse=True)
        bear_reasons.sort(key=lambda x: x[0], reverse=True)

        top_bull = f"[{bull_reasons[0][2]}] {bull_reasons[0][1]}" if bull_reasons else "N/A"
        top_bear = f"[{bear_reasons[0][2]}] {bear_reasons[0][1]}" if bear_reasons else "N/A"

        # Notable dissent: the highest-confidence opinion that goes against the majority
        if bull_count > bear_count and bear_reasons:
            notable_dissent = f"[{bear_reasons[0][2]}] 反对: {bear_reasons[0][1]}"
        elif bear_count > bull_count and bull_reasons:
            notable_dissent = f"[{bull_reasons[0][2]}] 支持: {bull_reasons[0][1]}"
        else:
            notable_dissent = "观点均匀分布，无明显异议"

        consensus.append(
            ConsensusItem(
                ticker=trade.ticker,
                action=trade.action,
                b216_score=round(b216_score, 3),
                consensus_level=consensus_level,
                bull_count=bull_count,
                bear_count=bear_count,
                neutral_count=neutral_count,
                top_bull_reason=top_bull[:300],
                top_bear_reason=top_bear[:300],
                notable_dissent=notable_dissent[:300],
            )
        )

    return consensus


# ─── Main Engine ──────────────────────────────────────────────────────


async def run_council(
    portfolio: Portfolio,
    master_ids: Optional[list[str]] = None,
    model: str = DEFAULT_MODEL,
    max_concurrent: int = 10,
    api_key: Optional[str] = None,
) -> CouncilReport:
    """Run the full council consultation.

    Args:
        portfolio: The portfolio to analyze.
        master_ids: Optional list of specific master IDs to consult. None = all.
        model: LLM model to use.
        max_concurrent: Max number of concurrent API calls.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.AsyncAnthropic(api_key=key)

    # Select masters
    if master_ids:
        masters = [m for m in MASTERS if m["id"] in master_ids]
    else:
        masters = MASTERS

    # Run all consultations in parallel with concurrency limit
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_consult(master: dict) -> MasterOpinion:
        async with semaphore:
            return await consult_master(client, master, portfolio, model)

    opinions = await asyncio.gather(*[limited_consult(m) for m in masters])

    # Aggregate consensus
    consensus = _aggregate_consensus(list(opinions), portfolio)

    # Generate overall summary
    summary_parts = []
    for ci in consensus:
        score_emoji = (
            "🟢" if ci.b216_score > 0.3
            else "🔴" if ci.b216_score < -0.3
            else "🟡"
        )
        summary_parts.append(
            f"{score_emoji} {ci.action.upper()} {ci.ticker}: "
            f"B216 Score {ci.b216_score:+.2f} "
            f"({ci.consensus_level.replace('_', ' ')}, "
            f"看多{ci.bull_count}/看空{ci.bear_count}/中性{ci.neutral_count})"
        )

    overall_summary = "\n".join(summary_parts) if summary_parts else "No trades to evaluate."

    return CouncilReport(
        opinions=list(opinions),
        consensus=consensus,
        overall_summary=overall_summary,
    )
