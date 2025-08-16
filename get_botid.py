import asyncio
import twitchio
from dotenv import load_dotenv
import os

async def main() -> None:
    load_dotenv()
    async with twitchio.Client(client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET")) as client:
        await client.login()
        user = await client.fetch_users(logins=["Albotzo"])
        for u in user:
            print(f"User: {u.name} - ID: {u.id}")

if __name__ == "__main__":
    asyncio.run(main())