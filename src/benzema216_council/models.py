"""Data models for BENZEMA216 Council."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    REDUCE = "reduce"
    SELL = "sell"


class Position(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    market: str = "us"  # us, hk, cn

    @property
    def cost_basis(self) -> float:
        return self.shares * self.avg_cost


class ProposedTrade(BaseModel):
    ticker: str
    action: str  # buy, sell, short
    shares: float
    reason: Optional[str] = None
    market: str = "us"


class Portfolio(BaseModel):
    cash: float = 0.0
    positions: list[Position] = Field(default_factory=list)
    proposed_trades: list[ProposedTrade] = Field(default_factory=list)
    context: str = ""  # optional market context or user notes


class TradeReview(BaseModel):
    ticker: str
    action: str
    verdict: Verdict
    confidence: int = Field(ge=0, le=100)
    reasoning: str


class MasterOpinion(BaseModel):
    master_id: str
    master_name: str
    master_name_cn: str
    school: str
    portfolio_assessment: str
    trade_reviews: list[TradeReview]
    key_advice: str


class ConsensusItem(BaseModel):
    ticker: str
    action: str
    b216_score: float = Field(ge=-1.0, le=1.0)  # -1 = strong sell, +1 = strong buy
    consensus_level: str  # "strong_consensus", "moderate_consensus", "divided"
    bull_count: int
    bear_count: int
    neutral_count: int
    top_bull_reason: str
    top_bear_reason: str
    notable_dissent: str


class CouncilReport(BaseModel):
    opinions: list[MasterOpinion]
    consensus: list[ConsensusItem]
    overall_summary: str
