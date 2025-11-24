"""Entrypoint for the Rolimon's OP Discord bot."""
from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

from src.alerts.manager import AlertManager
from src.commands import alert as alert_commands
from src.commands import op as op_commands
from src.config import settings
from src.data.op_service import OpService
from src.data.rolimons_client import RolimonsClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RolimonsBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.client = RolimonsClient()
        self.service = OpService(self.client)
        self.alert_manager = AlertManager(self.service)

    async def setup_hook(self) -> None:
        op_commands.setup(self.tree, self.service, self.client)
        alert_commands.setup(self.tree, self.alert_manager)
        if settings.guild_id:
            guild = discord.Object(id=settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        await self.alert_manager.start_polling(self)

    async def on_ready(self) -> None:
        logger.info("Logged in as %s", self.user)


def main() -> None:
    token = settings.token
    bot = RolimonsBot()
    try:
        bot.run(token, log_handler=None)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        asyncio.run(bot.client.close())


if __name__ == "__main__":
    main()
