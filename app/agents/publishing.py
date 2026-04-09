from app.agents.base import BaseAgent
from app.services.platforms import publish_to_platform


class PublishingAgent(BaseAgent):
    """
    Publie ou planifie la publication sur TikTok / Instagram.
    Entrées : video URL, platform, caption, hashtags, scheduled_at
    Sorties : platform_post_id, statut
    """

    name = "publishing"

    async def execute(self, input_data: dict) -> dict:
        video_url = input_data["video_file_url"]
        platform = input_data["platform"]
        caption = input_data.get("caption", "")
        hashtags = input_data.get("hashtags", [])

        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(f"#{h}" for h in hashtags)

        result = await publish_to_platform(
            platform=platform,
            video_url=video_url,
            caption=full_caption,
        )

        return {
            "platform_post_id": result.get("post_id"),
            "status": result.get("status", "published"),
        }
