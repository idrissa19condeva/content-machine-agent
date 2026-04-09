# Content Machine — Plateforme de Contenu IA Automatisé

Système semi-automatisé de création et publication de vidéos courtes (TikTok / Instagram Reels) alimenté par des agents IA.

## Stack Technique

- **Backend**: Python 3.12 + FastAPI
- **BDD**: PostgreSQL 16
- **Queue**: Redis + Celery
- **Stockage**: MinIO (S3-compatible)
- **Vidéo**: FFmpeg
- **LLM**: OpenAI GPT-4o / Anthropic Claude
- **TTS**: ElevenLabs / OpenAI TTS
- **Scheduler**: Celery Beat

## Démarrage rapide

```bash
# 1. Cloner et configurer
cp .env.example .env
# Remplir les clés API dans .env

# 2. Lancer l'infrastructure
docker-compose up -d

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
alembic upgrade head

# 5. Lancer l'API
uvicorn app.main:app --reload

# 6. Lancer le worker Celery
celery -A app.workers.celery_app worker --loglevel=info

# 7. Lancer le scheduler
celery -A app.workers.celery_app beat --loglevel=info
```

## Architecture

```
Trend Agent → Script Agent → Hook Optimizer → Voice Agent → Video Agent → Publishing Agent
                                                                              ↓
                                                              Analytics Agent → Feedback Agent
```

## Pipeline

1. **Idéation** — Détection de tendances + génération d'idées
2. **Script** — Rédaction optimisée (hook + corps + CTA)
3. **Audio** — Génération voix off TTS
4. **Vidéo** — Assemblage (fond + sous-titres + musique + branding)
5. **Publication** — Planification + push vers TikTok/IG
6. **Analytics** — Collecte métriques + boucle d'apprentissage
