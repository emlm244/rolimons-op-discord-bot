from __future__ import annotations

import logging
import os

import nextcord
from nextcord.ext import commands

from .rolimons_client import ItemNotFoundError, RolimonsError, get_item, percentile_bands

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

INTENTS = nextcord.Intents.none()


class OPBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix=commands.when_mentioned_or("/"), intents=INTENTS)

    async def on_ready(self) -> None:
        LOGGER.info("Logged in as %s", self.user)


bot = OPBot()


@bot.slash_command(description="Fetch typical OP ranges for a Rolimon's limited item")
async def op(  # type: ignore[override]
    interaction: nextcord.Interaction,
    item_id: int = nextcord.SlashOption(description="Roblox item id", required=True),
) -> None:
    await interaction.response.defer()
    try:
        details, history = await get_item(item_id)
        op_values = history.last_month_ops()
        small, fair, big = percentile_bands(op_values)
    except ItemNotFoundError:
        await interaction.followup.send(f"Item {item_id} not found on Rolimon's.")
        return
    except RolimonsError as exc:
        LOGGER.exception("Rolimons error")
        await interaction.followup.send(f"Failed to fetch item data: {exc}")
        return
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Unexpected error")
        await interaction.followup.send("Unexpected error while computing OP.")
        return

    embed = nextcord.Embed(
        title=details.name,
        description=f"RAP: {details.rap:,}\nValue: {details.value or 'N/A'}",
        color=nextcord.Color.blue(),
    )
    if details.thumbnail_url:
        embed.set_thumbnail(url=details.thumbnail_url)

    embed.add_field(name="Small OP (25th %)", value=f"{small:,} value", inline=False)
    embed.add_field(name="Fair OP (50th %)", value=f"{fair:,} value", inline=False)
    embed.add_field(name="Big OP (75th %)", value=f"{big:,} value", inline=False)
    embed.set_footer(text="Based on Rolimon's monthly history")

    await interaction.followup.send(embed=embed)


def main() -> None:
    token: str | None = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is required")
    bot.run(token)


if __name__ == "__main__":
    main()
