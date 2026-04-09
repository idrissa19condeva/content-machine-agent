from app.agents.base import BaseAgent
from app.services.llm import llm_completion


class ScriptWriterAgent(BaseAgent):
    """
    Agent de rédaction de scripts.
    Entrées : topic, hook, niche, langue, durée cible
    Sorties : script structuré (hook + body + CTA)
    Moment : après validation d'une idée
    """

    name = "script_writer"

    async def execute(self, input_data: dict) -> dict:
        topic = input_data["topic"]
        hook = input_data.get("hook", "")
        niche = input_data.get("niche", "business_tips")
        language = input_data.get("language", "fr")
        duration = input_data.get("target_duration_sec", 45)

        # ~150 mots par minute pour la voix off
        target_words = int((duration / 60) * 150)

        prompt = f"""Tu es un scriptwriter expert en vidéos courtes virales TikTok/Reels.

Sujet : {topic}
Accroche suggérée : {hook}
Niche : {niche}
Langue : {language}
Durée cible : {duration} secondes (~{target_words} mots)

Écris un script optimisé avec :
1. HOOK (5 sec) : accroche ultra-percutante, crée la curiosité
2. BODY (30-35 sec) : contenu de valeur, rythme rapide, phrases courtes
3. CTA (5 sec) : appel à l'action (follow, like, commentaire)

Règles :
- Phrases courtes et percutantes
- Langage naturel, pas trop corporate
- Chaque phrase doit donner envie d'écouter la suivante
- Adapté à un format voix off

Réponds UNIQUEMENT en JSON :
{{"hook": "...", "body": "...", "cta": "...", "full_text": "...", "word_count": N, "estimated_duration_sec": N}}"""

        result = await llm_completion(prompt, response_format="json")
        return result
