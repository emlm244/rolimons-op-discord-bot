"""Alert commands."""
from __future__ import annotations

import discord
from discord import app_commands

from src.alerts.manager import AlertManager
from src.config import settings


class AlertCommands(app_commands.Group):
    def __init__(self, manager: AlertManager) -> None:
        super().__init__(name="alert", description="Manage OP alerts")
        self.manager = manager

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_guild:
            return True
        if settings.staff_role_ids:
            return any(role.id in settings.staff_role_ids for role in getattr(interaction.user, "roles", []))
        return False

    @app_commands.command(name="add")
    @app_commands.describe(item_id="Roblox limited item id", min_op="Trigger threshold")
    async def add(self, interaction: discord.Interaction, item_id: int, min_op: int) -> None:
        if not self._is_staff(interaction):
            await interaction.response.send_message("This command is restricted to staff.", ephemeral=True)
            return
        if min_op <= 0:
            await interaction.response.send_message("min_op must be positive", ephemeral=True)
            return
        added = self.manager.add_alert(interaction, item_id, min_op)
        if not added:
            await interaction.response.send_message(
                f"Rate limited. Please wait {settings.alert_rate_limit_seconds}s before adding another alert.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Alert configured for item {item_id} when typical OP reaches {min_op}.", ephemeral=True
        )


def setup(tree: discord.app_commands.CommandTree, manager: AlertManager) -> None:
    tree.add_command(AlertCommands(manager))
