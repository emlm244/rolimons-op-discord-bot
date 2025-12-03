"""Main Discord bot for RISniper."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

import discord
from discord import app_commands

from src.config import config
from src.sniper.engine import SniperEngine, Opportunity
from src.data.roblox_client import PurchaseResult
from src.data.models import PurchaseRecord
from src.analytics.tracker import AnalyticsTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class RISniperBot(discord.Client):
    """Main Discord bot client for RISniper."""

    def __init__(self) -> None:
        """Initialize the bot."""
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.engine: Optional[SniperEngine] = None
        self.tracker: Optional[AnalyticsTracker] = None
        self.alert_channel: Optional[discord.TextChannel] = None

        # Pending confirmations (opportunity_id -> Opportunity)
        self._pending_confirmations: dict[str, Opportunity] = {}

    async def setup_hook(self) -> None:
        """Called when the bot is ready to set up."""
        # Initialize analytics tracker (for P&L tracking)
        self.tracker = AnalyticsTracker()
        await self.tracker.start()
        logger.info("Analytics tracker initialized")

        # Initialize sniper engine
        self.engine = SniperEngine()

        # Register callbacks
        self.engine.on_opportunity(self._on_opportunity)
        self.engine.on_purchase(self._on_purchase)

        # Import and register commands
        from src.commands.snipe import setup_snipe_commands
        from src.commands.config_cmd import setup_config_commands
        from src.commands.analyze import setup_analyze_commands
        from src.commands.stats import setup_stats_commands

        setup_snipe_commands(self)
        setup_config_commands(self)
        setup_analyze_commands(self)
        setup_stats_commands(self)

        # Sync commands
        if config.discord_guild_id:
            guild = discord.Object(id=config.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {config.discord_guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Set presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for snipes",
            )
        )

    async def _on_opportunity(self, opportunity: Opportunity) -> None:
        """Handle opportunity detected by engine."""
        from src.utils.embeds import build_opportunity_embed
        from src.config import PurchaseMode

        if not self.alert_channel:
            # Try to find a channel named "sniper-alerts" or use first text channel
            for guild in self.guilds:
                for channel in guild.text_channels:
                    if "sniper" in channel.name.lower() or "alert" in channel.name.lower():
                        self.alert_channel = channel
                        break
                if self.alert_channel:
                    break

            if not self.alert_channel and self.guilds:
                # Fallback to first text channel we can write to
                for channel in self.guilds[0].text_channels:
                    if channel.permissions_for(self.guilds[0].me).send_messages:
                        self.alert_channel = channel
                        break

        if not self.alert_channel:
            logger.warning("No alert channel found")
            return

        embed = build_opportunity_embed(opportunity)

        # Create view with buttons based on purchase mode
        view = OpportunityView(opportunity, self)

        await self.alert_channel.send(embed=embed, view=view)

    async def _on_purchase(
        self, opportunity: Opportunity, result: PurchaseResult
    ) -> None:
        """Handle purchase result from engine."""
        from src.utils.embeds import build_success_embed, build_error_embed
        from datetime import datetime
        import uuid

        # Record purchase in analytics tracker
        if self.tracker:
            strategy = (
                config.strategy_flags_list[0]
                if config.strategy_flags_list
                else "unknown"
            )
            record = PurchaseRecord(
                record_id=str(uuid.uuid4()),
                item_id=opportunity.item.item_id,
                item_name=opportunity.item.name,
                purchase_price=opportunity.listing.price,
                purchase_time=datetime.utcnow(),
                seller_id=opportunity.listing.seller_id,
                snipe_score=opportunity.score,
                strategy_used=strategy,
                success=(result == PurchaseResult.SUCCESS),
                current_value=opportunity.item.value,
                current_rap=opportunity.item.rap,
            )
            self.tracker.record_purchase(record)
            logger.info(f"Recorded purchase: {opportunity.item.name} - {'SUCCESS' if result == PurchaseResult.SUCCESS else 'FAILED'}")

        if not self.alert_channel:
            return

        if result == PurchaseResult.SUCCESS:
            embed = build_success_embed(
                "Purchase Successful!",
                f"Bought **{opportunity.item.name}** for **{opportunity.listing.price:,} R$**\n"
                f"Score: {opportunity.score}/100 | Discount: {opportunity.score_result.discount_percent:.1f}%",
            )
        else:
            embed = build_error_embed(
                "Purchase Failed",
                f"Failed to buy **{opportunity.item.name}**\n"
                f"Reason: {result.value}",
            )

        await self.alert_channel.send(embed=embed)

    async def close(self) -> None:
        """Clean up on shutdown."""
        if self.tracker:
            await self.tracker.close()
        if self.engine:
            await self.engine.close()
        await super().close()


class OpportunityView(discord.ui.View):
    """View with buttons for opportunity alerts."""

    def __init__(self, opportunity: Opportunity, bot: RISniperBot) -> None:
        super().__init__(timeout=300)  # 5 minute timeout
        self.opportunity = opportunity
        self.bot = bot

    @discord.ui.button(label="BUY NOW", style=discord.ButtonStyle.success, emoji="")
    async def buy_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Handle buy button click."""
        await interaction.response.defer()

        if not self.bot.engine:
            await interaction.followup.send("Engine not initialized", ephemeral=True)
            return

        # Execute purchase
        result = await self.bot.engine.manual_purchase(self.opportunity)

        if result == PurchaseResult.SUCCESS:
            button.disabled = True
            button.label = "PURCHASED"
            await interaction.message.edit(view=self)
            await interaction.followup.send(
                f"Successfully purchased **{self.opportunity.item.name}**!",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"Purchase failed: {result.value}",
                ephemeral=True,
            )

    @discord.ui.button(label="SKIP", style=discord.ButtonStyle.secondary)
    async def skip_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Handle skip button click."""
        self.buy_button.disabled = True
        button.disabled = True
        button.label = "SKIPPED"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="DETAILS", style=discord.ButtonStyle.primary, emoji="")
    async def details_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Show detailed analysis."""
        from src.utils.embeds import build_analyze_embed

        embed = build_analyze_embed(self.opportunity.score_result)
        await interaction.response.send_message(embed=embed, ephemeral=True)


def run_bot() -> None:
    """Run the bot."""
    # Validate config
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Config error: {error}")
        sys.exit(1)

    bot = RISniperBot()
    bot.run(config.discord_token)


if __name__ == "__main__":
    run_bot()
