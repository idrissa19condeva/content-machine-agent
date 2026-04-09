from app.agents.base import BaseAgent
from app.services.platforms import fetch_metrics
from app.services.llm import llm_completion


class AnalyticsAgent(BaseAgent):
    """
    Collecte les métriques de performance d'un post publié.
    Entrées : platform, platform_post_id
    Sorties : views, likes, comments, shares, engagement_rate
    """

    name = "analytics"

    async def execute(self, input_data: dict) -> dict:
        platform = input_data["platform"]
        post_id = input_data["platform_post_id"]

        metrics = await fetch_metrics(platform=platform, post_id=post_id)

        total_interactions = metrics["likes"] + metrics["comments"] + metrics["shares"]
        views = max(metrics["views"], 1)
        metrics["engagement_rate"] = round(total_interactions / views * 100, 2)

        return metrics


class FeedbackLearningAgent(BaseAgent):
    """
    Analyse les performances passées et génère des recommandations
    pour améliorer les futurs contenus.
    Entrées : liste de posts avec métriques
    Sorties : insights, patterns identifiés, recommandations
    """

    name = "feedback_learning"

    async def execute(self, input_data: dict) -> dict:
        posts_data = input_data["posts_with_metrics"]
        niche = input_data.get("niche", "business_tips")

        prompt = f"""Tu es un analyste de contenu TikTok/Reels expert.
Niche : {niche}

Voici les performances de nos derniers posts :
{_format_posts(posts_data)}

Analyse ces données et donne :
1. Les patterns qui fonctionnent (hooks, sujets, formats)
2. Ce qui ne fonctionne pas
3. 5 recommandations concrètes pour les prochains contenus
4. Les meilleurs horaires de publication identifiés
5. Les types de hooks les plus performants

Réponds en JSON :
{{"top_patterns": [...], "weak_patterns": [...], "recommendations": [...], "best_posting_times": [...], "best_hook_types": [...]}}"""

        return await llm_completion(prompt, response_format="json")


def _format_posts(posts: list) -> str:
    lines = []
    for p in posts[:20]:  # max 20 pour le contexte
        lines.append(
            f"- Topic: {p.get('topic')} | Hook: {p.get('hook')} | "
            f"Views: {p.get('views',0)} | Likes: {p.get('likes',0)} | "
            f"Engagement: {p.get('engagement_rate',0)}%"
        )
    return "\n".join(lines)
