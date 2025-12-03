# RISniper

**Intelligent Roblox Limited Item Sniper Bot**

A sophisticated Discord bot that uses a multi-factor scoring algorithm to identify and snipe profitable Roblox limited item deals. This is NOT a "buy anything cheap" bot - it uses data-driven analysis to filter out traps and find genuinely profitable opportunities.

## Features

### The Algorithm

The scoring system evaluates each opportunity on a 0-100 scale:

| Factor | Points | Description |
|--------|--------|-------------|
| Discount | 0-30 | How far below value is the price? |
| Demand | 0-25 | Rolimons demand rating |
| Trend | 0-20 | Is value stable/rising? |
| Liquidity | 0-15 | Recent sales volume |
| Stability | 0-10 | Does RAP match value? |

Plus bonuses for rare items with high demand, and penalties for UGC/hyped items.

### Pre-Filters (Hard Rejects)

Items are instantly rejected if:
- Marked as **projected** (artificially inflated)
- Terrible or no demand
- Actively lowering trend
- UGC item less than 30 days old
- Fewer than 5 copies remaining
- No sales in 90 days

### Score Tiers

| Score | Tier | Action |
|-------|------|--------|
| 85-100 | EXCELLENT | Auto-buy (in full auto mode) |
| 70-84 | GOOD | Alert + optional auto-buy |
| 50-69 | RISKY | Alert only |
| 0-49 | REJECT | Ignored |

### Trading Strategies

Choose your style:

- **Quick Flips** - High-liquidity items for fast resale
- **Value Plays** - Deep discounts on stable items
- **Rare Hunting** - Rare items with high demand (high risk/reward)

### Purchase Modes

- **Alert + Confirm** (default) - Bot alerts, you click to buy
- **Full Auto** - Bot buys automatically when threshold met
- **Hybrid** - Auto for 85+, confirm for 70-84

## Commands

| Command | Description |
|---------|-------------|
| `/snipe start` | Start the sniper engine |
| `/snipe stop` | Stop the sniper engine |
| `/snipe status` | Show current status |
| `/config mode` | Set purchase mode |
| `/config strategy` | Set trading strategy |
| `/config ugc` | Set UGC handling |
| `/config threshold` | Set score threshold |
| `/config budget` | Set max price per item |
| `/config info` | Show all settings |
| `/analyze <item_id>` | Analyze an item's snipe score |
| `/lookup <item_id>` | Quick item info lookup |
| `/stats overview` | Portfolio statistics |
| `/stats session` | Current session stats |

## Setup

### 1. Clone and Install

```bash
git clone https://github.com/emlm244/rolimons-op-discord-bot.git
cd rolimons-op-discord-bot
pip install -r requirements.txt
```

### 2. Configure

Copy `.env.example` to `.env` and fill in:

```env
# Required
DISCORD_TOKEN=your_bot_token
ROBLOSECURITY=your_.ROBLOSECURITY_cookie

# Optional
DISCORD_GUILD_ID=your_guild_id
SNIPE_THRESHOLD=70
MAX_PRICE_PER_ITEM=50000
TOTAL_BUDGET=500000
```

### 3. Run

```bash
python -m src.bot
```

## Project Structure

```
src/
├── bot.py                 # Discord bot entrypoint
├── config.py              # Configuration management
├── sniper/
│   ├── scorer.py          # THE ALGORITHM
│   ├── engine.py          # Main sniper loop
│   └── executor.py        # Purchase execution
├── data/
│   ├── models.py          # Data models
│   ├── rolimons_client.py # Rolimons API
│   └── roblox_client.py   # Roblox Economy API
├── analysis/
│   └── filters.py         # Pre-filters
├── commands/              # Discord commands
├── analytics/             # P&L tracking
└── utils/                 # Utilities
```

## How It Works

1. **Polling**: Engine fetches item data from Rolimons every 60s
2. **Filtering**: Items run through pre-filters (projected, demand, etc.)
3. **Scoring**: Passing items scored by the algorithm
4. **Action**: Based on score and mode, auto-buy or alert
5. **Tracking**: All decisions logged, P&L tracked

## Safety Features

- Per-item and total budget limits
- Purchase rate limiting (max/hour)
- Cooldown between purchases
- Listing verification before buy
- Kill switch via `/snipe stop`

## Data Sources

- [Rolimons](https://www.rolimons.com) - Item values, demand, trends
- [Roblox Economy API](https://economy.roblox.com) - Resellers, purchases

## License

MIT

## Disclaimer

This bot is for educational purposes. Use at your own risk. The developers are not responsible for any losses incurred from trading Roblox limiteds.
