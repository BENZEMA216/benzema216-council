# BENZEMA216 Council

Swarm intelligence investment council — 21 legendary investors analyze your portfolio.

## What is this?

Input your portfolio and proposed trades, and 20 investment masters (中美各半) will independently evaluate each trade from their unique philosophy. A council then aggregates their opinions using weighted voting to produce consensus scores, identify areas of agreement/disagreement, and highlight notable dissenting views.

## Masters (20)

### US (12)
| Master | School |
|--------|--------|
| Warren Buffett | Value investing, moats |
| Charlie Munger | Mental models, quality |
| Benjamin Graham | Deep value, margin of safety |
| Seth Klarman | Risk-averse value |
| Howard Marks | Cycles, second-level thinking |
| Joel Greenblatt | Magic formula |
| Peter Lynch | Growth at reasonable price |
| Philip Fisher | Scuttlebutt growth |
| George Soros | Reflexivity, macro |
| Ray Dalio | All weather, risk parity |
| Stanley Druckenmiller | Macro, concentrated bets |
| Jim Simons | Quantitative, statistical |
| John Bogle | Passive indexing |

### China (8)
| Master | School |
|--------|--------|
| 李录 Li Lu | Value investing in China |
| 段永平 Duan Yongping | Business model focus |
| 张磊 Zhang Lei | Long-termism |
| 邱国鹭 Qiu Guolu | Simple investing |
| 但斌 Dan Bin | Time's rose |
| 冯柳 Feng Liu | Weak-party contrarian |
| 赵军 Zhao Jun | Contrarian gold-panning |
| 葛卫东 Ge Weidong | Macro + futures |

## Quick Start

```bash
# Install
cd benzema216-council
pip install -e .

# Set API key
export ANTHROPIC_API_KEY=sk-ant-xxx

# Run with example portfolio
b216 examples/portfolio.yaml

# Only Chinese masters
b216 examples/portfolio.yaml --region cn

# Specific masters
b216 examples/portfolio.yaml --masters warren_buffett,li_lu,george_soros

# Detailed view of one master
b216 examples/portfolio.yaml --detail warren_buffett

# Save raw JSON
b216 examples/portfolio.yaml -o report.json

# List all masters
b216 --list-masters
```

## Portfolio YAML Format

```yaml
cash: 50000

positions:
  - ticker: AAPL
    shares: 100
    avg_cost: 178.50
    market: us

proposed_trades:
  - ticker: TSLA
    action: buy
    shares: 30
    market: us
    reason: "AI + robotics thesis"

context: |
  Any market context or personal notes.
```

## How It Works

1. **Fan-out**: All 21 masters receive your portfolio simultaneously (async parallel)
2. **Independent analysis**: Each master evaluates every proposed trade from their unique philosophy
3. **Structured output**: Each master returns verdict (strong_buy → sell), confidence (0-100), and reasoning
4. **Council aggregation**: Weighted voting produces a B216 Score (-1.0 to +1.0) per trade
5. **Dissent detection**: Highlights where strong disagreements exist between schools of thought

## Architecture

```
Portfolio YAML
     │
     ▼
┌─────────────────────────────────────────┐
│  Fan-out: 21 parallel LLM calls         │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │ Buffett  │ │ Soros   │ │ 李录     │  │
│  │ Graham   │ │ Dalio   │ │ 段永平   │  │
│  │ Munger   │ │ Druck.  │ │ 张磊     │  │
│  │ ...      │ │ ...     │ │ ...      │  │
│  └────┬─────┘ └────┬────┘ └────┬─────┘  │
│       └─────────────┼──────────┘         │
│                     ▼                    │
│         ┌───────────────────┐            │
│         │  Council (Swarm)  │            │
│         │  Weighted voting  │            │
│         │  Consensus detect │            │
│         │  Dissent highlight│            │
│         └───────────────────┘            │
└─────────────────────────────────────────┘
     │
     ▼
  Rich CLI Report / JSON
```

## Inspired By

- [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) — AI agents as famous investors
- BENZEMA216 Council extends this with Chinese masters, portfolio-centric analysis, and swarm intelligence
