from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .config import settings
from .data import Item, RolimonsClient, calculate_op_ranges, calculate_typical_op
from .rate_limiter import SlidingWindowRateLimiter
from .storage import Alert, AlertStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_embed(item: Item, typical_op: float | None, proofs_count: int) -> discord.Embed:
    embed = discord.Embed(title=item.name, color=discord.Color.blue())
    if item.value:
        embed.add_field(name="Value", value=f"{item.value:,}", inline=True)
    if item.rap:
        embed.add_field(name="RAP", value=f"{item.rap:,}", inline=True)
    if item.demand:
        embed.add_field(name="Demand", value=item.demand, inline=True)
    if typical_op is not None:
        embed.add_field(name="Typical OP (30d avg)", value=f"{int(typical_op):,}", inline=False)
    ranges = calculate_op_ranges(typical_op)
    if ranges:
        embed.add_field(
            name="OP Ranges",
            value=f"Small: {ranges['small']}\nFair: {ranges['fair']}\nBig: {ranges['big']}",
            inline=False,
        )
    embed.add_field(name="Recent proofs (30d)", value=str(proofs_count), inline=True)
    embed.timestamp = datetime.utcnow()
    if item.thumbnail_url:
        embed.set_thumbnail(url=item.thumbnail_url)
    return embed


class ProofsView(discord.ui.View):
    def __init__(self, proofs_summary: str):
        super().__init__(timeout=60)
        self.proofs_summary = proofs_summary

    @discord.ui.button(label="DM proofs", style=discord.ButtonStyle.primary)
    async def send_proofs(self, interaction: discord.Interaction, _: discord.ui.Button):
        try:
            await interaction.user.send(self.proofs_summary)
            await interaction.response.send_message("Sent proofs to your DMs.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't send you a DM. Please check your privacy settings.",
                ephemeral=True,
            )


class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.rolimons = RolimonsClient()
        self.alert_store = AlertStore()
        self.rate_limiter = SlidingWindowRateLimiter(max_calls=5, window_seconds=60)
        self.alert_task.start()

    async def setup_hook(self) -> None:
        guilds = [discord.Object(id=g) for g in settings.guild_ids] if settings.guild_ids else None
        if guilds:
            for guild in guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        logger.info("Bot connected as %s", self.user)

    async def close(self) -> None:
        await self.rolimons.aclose()
        await super().close()

    def is_staff(self, interaction: discord.Interaction) -> bool:
        perms = interaction.user.guild_permissions
        return perms.manage_guild or perms.administrator

    @tasks.loop(seconds=settings.alert_poll_seconds)
    async def alert_task(self):
        await self.wait_until_ready()
        for alert in self.alert_store.list_all():
            proofs = await self.rolimons.fetch_proofs(alert.item_id, months=6)
            if not proofs:
                continue
            latest = proofs[0]
            if latest.op >= alert.min_op:
                user = self.get_user(alert.user_id)
                if user is None:
                    try:
                        user = await self.fetch_user(alert.user_id)
                    except discord.HTTPException:
                        user = None
                if user:
                    try:
                        message = (
                            f"Alert: {alert.item_name} has recent OP {latest.op:,} "
                            f"on {latest.date.date()}"
                        )
                        await user.send(message)
                    except discord.Forbidden:
                        logger.warning("Failed to DM user %s", alert.user_id)

    @alert_task.before_loop
    async def before_alert_task(self):
        await self.wait_until_ready()


bot = Bot()


@bot.tree.command(name="op", description="Fetch Rolimon's OP data for a limited item")
@app_commands.describe(item="Limited item name")
async def op_command(interaction: discord.Interaction, item: str):
    if not bot.rate_limiter.allow(interaction.user.id):
        await interaction.response.send_message(
            "Slow down a bit. Please retry in a few seconds.", ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)
    matched = await bot.rolimons.search_item(item)
    if not matched:
        await interaction.followup.send("Item not found.", ephemeral=True)
        return

    proofs = await bot.rolimons.fetch_proofs(matched.item_id, months=6)
    typical_op = calculate_typical_op(proofs, months=1)
    recent_month = [p for p in proofs if (datetime.utcnow() - p.date).days <= 30]
    embed = build_embed(matched, typical_op, len(recent_month))

    proofs_summary = "\n".join(
        [f"{p.date.date()}: {p.op:,} OP - {p.description}".strip() for p in proofs[:10]]
    )
    view = ProofsView(proofs_summary or "No proofs found in the last 6 months.")

    await interaction.followup.send(embed=embed, view=view, ephemeral=False)


@bot.tree.command(name="alert", description="Manage OP alerts")
@app_commands.describe(item="Limited item name", min_op="Minimum OP to alert on")
async def alert_add(interaction: discord.Interaction, item: str, min_op: int):
    if not bot.is_staff(interaction):
        await interaction.response.send_message(
            "You need Manage Server permissions to add alerts.", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    matched = await bot.rolimons.search_item(item)
    if not matched:
        await interaction.followup.send("Item not found.")
        return
    alert = Alert(
        guild_id=interaction.guild_id or 0,
        user_id=interaction.user.id,
        item_id=matched.item_id,
        item_name=matched.name,
        min_op=min_op,
    )
    bot.alert_store.add_alert(alert)
    await interaction.followup.send(
        f"Alert saved for {matched.name} at {min_op:,} OP.", ephemeral=True
    )


async def main():
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN is required to start the bot")
    async with bot:
        await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
