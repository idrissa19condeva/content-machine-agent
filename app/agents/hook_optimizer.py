from app.agents.base import BaseAgent
from app.services.llm import llm_completion


class HookOptimizerAgent(BaseAgent):
    """
    Optimise le hook d'un script pour maximiser la rétention.
    Entrées : script complet, métriques passées (optionnel)
    Sorties : 3 variantes de hook classées par potentiel
    """

    name = "hook_optimizer"

    async def execute(self, input_data: dict) -> dict:
        script = input_data["full_text"]
        niche = input_data.get("niche", "business_tips")
        top_hooks = input_data.get("top_performing_hooks", [])

        context = ""
        if top_hooks:
            context = f"\nHooks qui ont le mieux performé par le passé :\n" + "\n".join(f"- {h}" for h in top_hooks[:5])

        prompt = f"""Tu es expert en rétention TikTok. Les 3 premières secondes décident tout.

Script actuel :
{script}

Niche : {niche}
{context}

Propose 3 variantes de hook, classées du plus fort au moins fort.
Chaque hook doit :
- Créer un "pattern interrupt" (casser le scroll)
- Provoquer curiosité ou émotion immédiate
- Faire moins de 15 mots

Réponds en JSON :
{{"hooks": [{{"text": "...", "technique": "curiosity_gap|shock|question|bold_claim", "confidence": 0.9}}]}}"""

        return await llm_completion(prompt, response_format="json")
