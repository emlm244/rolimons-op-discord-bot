"""Helper functions for Discord embeds."""
from __future__ import annotations

import discord


def op_embed(*, item_id: int, item_name: str, lower: int, upper: int, image_url: str, proofs: list[str] | None = None) -> discord.Embed:
    embed = discord.Embed(title=item_name or f"Item {item_id}", description=f"Typical OP range (30d): {lower} - {upper}")
    embed.set_thumbnail(url=image_url)
    embed.add_field(name="Lower", value=str(lower), inline=True)
    embed.add_field(name="Upper", value=str(upper), inline=True)
    embed.set_footer(text="Data courtesy of Rolimon's")
    if proofs:
        embed.add_field(name="Recent proofs", value="\n".join(proofs), inline=False)
    return embed
