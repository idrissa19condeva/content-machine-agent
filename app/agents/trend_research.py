from app.agents.base import BaseAgent
from app.services.llm import llm_completion


class TrendResearchAgent(BaseAgent):
    """
    Agent de recherche de tendances.
    Entrées : niche, langue, nombre d'idées souhaitées
    Sorties : liste d'idées de contenus avec score de tendance
    Moment : début du pipeline, déclenché manuellement ou par cron
    """

    name = "trend_research"

    async def execute(self, input_data: dict) -> dict:
        niche = input_data["niche"]
        language = input_data.get("language", "fr")
        count = input_data.get("count", 5)

        prompt = f"""Tu es un expert en contenu viral sur TikTok et Instagram Reels.
Niche : {niche}
Langue : {language}

Génère {count} idées de vidéos courtes (30-60 secondes) qui ont un fort potentiel viral.

Pour chaque idée, donne :
- topic: le sujet en une phrase
- hook: une accroche percutante (première phrase de la vidéo)
- trend_score: score de viralité estimé de 0 à 1
- reasoning: pourquoi ça peut fonctionner

Réponds UNIQUEMENT en JSON valide :
{{"ideas": [{{"topic": "...", "hook": "...", "trend_score": 0.8, "reasoning": "..."}}]}}"""

        result = await llm_completion(prompt, response_format="json")
        return result
