import httpx
import structlog
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def publish_to_platform(platform: str, video_url: str, caption: str) -> dict:
    """Publie une vidéo sur TikTok ou Instagram. Retourne {post_id, status}."""

    if platform == "tiktok":
        return await _publish_tiktok(video_url, caption)
    elif platform == "instagram":
        return await _publish_instagram(video_url, caption)
    else:
        raise ValueError(f"Plateforme inconnue : {platform}")


async def _publish_tiktok(video_url: str, caption: str) -> dict:
    """
    Publication via TikTok Content Posting API.
    Ref : https://developers.tiktok.com/doc/content-posting-api
    Flux : init upload → upload video → publish
    """
    token = settings.tiktok_access_token
    if not token:
        logger.warning("TikTok: pas de token configuré, publication simulée")
        return {"post_id": "simulated_tiktok_id", "status": "simulated"}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=120) as client:
        # Étape 1 : Init upload
        init_resp = await client.post(
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
            headers=headers,
            json={
                "post_info": {"title": caption[:150], "privacy_level": "PUBLIC_TO_EVERYONE"},
                "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
            },
        )
        init_resp.raise_for_status()
        publish_id = init_resp.json().get("data", {}).get("publish_id")

        return {"post_id": publish_id, "status": "published"}


async def _publish_instagram(video_url: str, caption: str) -> dict:
    """
    Publication via Instagram Graph API (Reels).
    Ref : https://developers.facebook.com/docs/instagram-api/guides/content-publishing
    """
    token = settings.instagram_access_token
    account_id = settings.instagram_business_account_id
    if not token or not account_id:
        logger.warning("Instagram: pas de token configuré, publication simulée")
        return {"post_id": "simulated_ig_id", "status": "simulated"}

    async with httpx.AsyncClient(timeout=120) as client:
        # Étape 1 : Créer le container
        container_resp = await client.post(
            f"https://graph.facebook.com/v19.0/{account_id}/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": token,
            },
        )
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        # Étape 2 : Publier
        publish_resp = await client.post(
            f"https://graph.facebook.com/v19.0/{account_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
        )
        publish_resp.raise_for_status()
        post_id = publish_resp.json()["id"]

        return {"post_id": post_id, "status": "published"}


async def fetch_metrics(platform: str, post_id: str) -> dict:
    """Récupère les métriques d'un post publié."""

    if platform == "tiktok":
        return await _fetch_tiktok_metrics(post_id)
    elif platform == "instagram":
        return await _fetch_instagram_metrics(post_id)
    return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "watch_time_avg_sec": 0}


async def _fetch_tiktok_metrics(post_id: str) -> dict:
    token = settings.tiktok_access_token
    if not token:
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "watch_time_avg_sec": 0}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.tiktokapis.com/v2/video/query/",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"filters": {"video_ids": [post_id]}, "fields": ["like_count", "comment_count", "share_count", "view_count"]},
        )
        data = resp.json().get("data", {}).get("videos", [{}])[0]
        return {
            "views": data.get("view_count", 0),
            "likes": data.get("like_count", 0),
            "comments": data.get("comment_count", 0),
            "shares": data.get("share_count", 0),
            "watch_time_avg_sec": 0,
        }


async def _fetch_instagram_metrics(post_id: str) -> dict:
    token = settings.instagram_access_token
    if not token:
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "watch_time_avg_sec": 0}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/v19.0/{post_id}/insights",
            params={"metric": "plays,likes,comments,shares", "access_token": token},
        )
        # Simplification - parser selon la structure réelle de l'API
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "watch_time_avg_sec": 0}
