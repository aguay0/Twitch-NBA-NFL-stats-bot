import asyncio
import twitchio
from twitchio import eventsub
from twitchio.ext import commands
import json
from dotenv import load_dotenv
import os
from CommandsComponent import CommandsComponent
import logging

load_dotenv()

LOGGER: logging.Logger = logging.getLogger(__name__)


class Bot(commands.AutoBot):

  def __init__(self, subs: list[eventsub.SubscriptionPayload]) -> None:
    super().__init__(client_id=os.getenv("CLIENT_ID"),
                     client_secret=os.getenv("CLIENT_SECRET"),
                     bot_id=os.getenv("BOT_ID"),
                     prefix='!',
                     subscriptions =subs,
                     force_subscribe = True)

  async def setup_hook(self) -> None:
    await self.add_component(CommandsComponent(self))

  async def event_ready(self) -> None :
    LOGGER.info("Successfully logged in as: %s", self.user)
  
  async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)
        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            # We usually don't want subscribe to events on the bots channel...
            return

        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
            eventsub.StreamOnlineSubscription(broadcaster_user_id=payload.user_id),
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            LOGGER.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

  async def event_message(self, payload: twitchio.ChatMessage) -> None:
      # Just for example purposes...
      LOGGER.info("[%s]: %s", payload.chatter, payload.text)
      await super().event_message(payload)

def main() -> None:
  twitchio.utils.setup_logging(level=logging.INFO)

  # For example purposes we are just using the default token storage, but you could store in a database etc..
  # Generate a list of subscriptions for each user token we have...
  subs: list[eventsub.SubscriptionPayload] = []

  with open(".tio.tokens.json", "rb") as fp:
      tokens = json.load(fp)
      for user_id in tokens:
          if user_id == os.getenv("BOT_ID"):
              continue
          
          subs.extend(
              [
                  eventsub.ChatMessageSubscription(broadcaster_user_id=user_id, user_id=os.getenv("BOT_ID")),
                  eventsub.StreamOnlineSubscription(broadcaster_user_id=user_id),
              ]
          )

  async def runner() -> None:
      async with Bot(subs=subs) as bot:
          await bot.start()

  try:
      asyncio.run(runner())
  except KeyboardInterrupt:
      LOGGER.warning("Shutting down due to KeyboardInterrupt.")


if __name__ == "__main__":
  main()