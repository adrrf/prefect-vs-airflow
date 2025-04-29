from prefect.blocks.notifications import DiscordWebhook
import os

try:
    discord_webhook = DiscordWebhook(
        webhook_id=os.environ["DISCORD_WEBHOOK_ID"],
        webhook_token=os.environ["DISCORD_WEBHOOK_TOKEN"],
    )
    discord_webhook.save("discord-failure", overwrite=True)
except Exception as e:
    print(f"Error creating Discord webhook block: {e}")
    raise
