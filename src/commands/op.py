"""Slash commands for OP lookups."""
from __future__ import annotations

import discord
from discord import app_commands

from src.config import settings
from src.data.op_service import OpService
from src.data.rolimons_client import RolimonsClient
from src.utils.embeds import op_embed


class OpCommands(app_commands.Group):
    def __init__(self, service: OpService, client: RolimonsClient) -> None:
        super().__init__(name="op", description="OP lookup commands")
        self.service = service
        self.client = client

    @app_commands.command(name="item")
    @app_commands.describe(item_id="Roblox limited item id", send_dm="Send proofs to DM")
    async def item(self, interaction: discord.Interaction, item_id: int, send_dm: bool = False) -> None:
        await interaction.response.defer(ephemeral=False)
        lower, upper = await self.service.get_typical_range(item_id)
        proofs = await self.service.get_recent_proofs(item_id, months=settings.dm_proofs_lookback_months)
        item_name = await self.client.fetch_item_name(item_id) or f"Item {item_id}"
        image_url = self.client.item_image_url(item_id)
        embed = op_embed(item_id=item_id, item_name=item_name, lower=lower, upper=upper, image_url=image_url)
        if send_dm and proofs:
            try:
                await interaction.user.send(embed=op_embed(item_id=item_id, item_name=item_name, lower=lower, upper=upper, image_url=image_url, proofs=proofs))
            except discord.Forbidden:
                await interaction.followup.send("Could not send DM. Check your privacy settings.", ephemeral=True)
        if proofs:
            embed.add_field(name="Proofs (latest)", value="\n".join(proofs), inline=False)
        await interaction.followup.send(embed=embed)


def setup(tree: discord.app_commands.CommandTree, service: OpService, client: RolimonsClient) -> None:
    tree.add_command(OpCommands(service, client))
