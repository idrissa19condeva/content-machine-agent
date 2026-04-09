from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
import time
import structlog
from app.models.entities import AgentRun

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Classe de base pour tous les agents IA du pipeline."""

    name: str = "base_agent"

    @abstractmethod
    async def execute(self, input_data: dict) -> dict:
        """Exécute la logique principale de l'agent."""
        ...

    async def run(self, input_data: dict, db_session=None) -> dict:
        """Wrapper avec logging, timing et audit trail."""
        start = time.time()
        run_record = AgentRun(
            agent_name=self.name,
            project_id=input_data.get("project_id"),
            input_data=input_data,
            status="running",
            started_at=datetime.utcnow(),
        )

        try:
            if db_session:
                db_session.add(run_record)
                await db_session.flush()

            logger.info(f"[{self.name}] Démarrage", input_keys=list(input_data.keys()))
            result = await self.execute(input_data)

            run_record.output_data = result
            run_record.status = "success"
            run_record.duration_ms = int((time.time() - start) * 1000)
            run_record.finished_at = datetime.utcnow()
            run_record.tokens_used = result.get("_tokens_used", 0)
            run_record.cost_usd = result.get("_cost_usd", 0.0)

            logger.info(f"[{self.name}] Terminé", duration_ms=run_record.duration_ms)
            return result

        except Exception as e:
            run_record.status = "failed"
            run_record.error = str(e)
            run_record.duration_ms = int((time.time() - start) * 1000)
            run_record.finished_at = datetime.utcnow()
            logger.error(f"[{self.name}] Erreur", error=str(e))
            raise
