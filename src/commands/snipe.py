"""Sniper control commands: /snipe start|stop|status."""

from __future__ import annotations

import discord
from discord import app_commands

from src.utils.embeds import build_status_embed, build_success_embed, build_error_embed


def setup_snipe_commands(bot) -> None:
    """Set up /snipe commands on the bot."""

    snipe_group = app_commands.Group(name="snipe", description="Sniper control commands")

    @snipe_group.command(name="start", description="Start the sniper engine")
    async def snipe_start(interaction: discord.Interaction) -> None:
        """Start the sniper engine."""
        await interaction.response.defer()

        if not bot.engine:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Engine not initialized"),
            )
            return

        if bot.engine.state.value == "running":
            await interaction.followup.send(
                embed=build_error_embed("Already Running", "Sniper is already running"),
            )
            return

        # Set alert channel to current channel
        bot.alert_channel = interaction.channel

        await bot.engine.start()

        await interaction.followup.send(
            embed=build_success_embed(
                "Sniper Started",
                f"Sniper engine is now running.\n"
                f"Alerts will be sent to this channel.",
            ),
        )

    @snipe_group.command(name="stop", description="Stop the sniper engine")
    async def snipe_stop(interaction: discord.Interaction) -> None:
        """Stop the sniper engine."""
        await interaction.response.defer()

        if not bot.engine:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Engine not initialized"),
            )
            return

        if bot.engine.state.value == "stopped":
            await interaction.followup.send(
                embed=build_error_embed("Already Stopped", "Sniper is not running"),
            )
            return

        await bot.engine.stop()

        await interaction.followup.send(
            embed=build_success_embed("Sniper Stopped", "Sniper engine has been stopped."),
        )

    @snipe_group.command(name="pause", description="Pause the sniper engine")
    async def snipe_pause(interaction: discord.Interaction) -> None:
        """Pause the sniper engine."""
        if not bot.engine:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Engine not initialized"),
                ephemeral=True,
            )
            return

        await bot.engine.pause()
        await interaction.response.send_message(
            embed=build_success_embed("Sniper Paused", "Sniper engine is paused."),
        )

    @snipe_group.command(name="resume", description="Resume the sniper engine")
    async def snipe_resume(interaction: discord.Interaction) -> None:
        """Resume the sniper engine."""
        if not bot.engine:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Engine not initialized"),
                ephemeral=True,
            )
            return

        await bot.engine.resume()
        await interaction.response.send_message(
            embed=build_success_embed("Sniper Resumed", "Sniper engine is running."),
        )

    @snipe_group.command(name="status", description="Show sniper status")
    async def snipe_status(interaction: discord.Interaction) -> None:
        """Show sniper status."""
        if not bot.engine:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Engine not initialized"),
                ephemeral=True,
            )
            return

        status = bot.engine.get_status()
        embed = build_status_embed(status)
        await interaction.response.send_message(embed=embed)

    # Add group to bot
    bot.tree.add_command(snipe_group)
