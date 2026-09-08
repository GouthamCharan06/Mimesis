"""Firestore-backed project repository implementation."""

from __future__ import annotations

from google.cloud import firestore

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.retry import with_provider_retry
from app.domain.models import PodcastSession
from app.providers.interfaces import SessionRepository

logger = get_logger(__name__)

SESSIONS_COLLECTION = "mimesis_podcast_sessions"


class FirestoreProjectRepository(SessionRepository):
    """Firestore implementation of the podcast session repository."""

    def __init__(self) -> None:
        settings = get_settings()
        self._db = firestore.AsyncClient(
            project=settings.google_cloud_project or None,
            database=settings.firestore_database,
        )
        logger.info("firestore_repository_initialized", database=settings.firestore_database)

    @property
    def _collection(self) -> firestore.AsyncCollectionReference:
        return self._db.collection(SESSIONS_COLLECTION)

    @with_provider_retry()
    async def create_session(self, session: PodcastSession) -> str:
        doc_ref = self._collection.document(session.session_id)
        await doc_ref.set(session.model_dump(mode="json"))
        logger.info("podcast_session_created", session_id=session.session_id)
        return session.session_id

    @with_provider_retry()
    async def get_session(self, session_id: str) -> PodcastSession | None:
        doc = await self._collection.document(session_id).get()
        if not doc.exists:
            return None
        return PodcastSession.model_validate(doc.to_dict())

    @with_provider_retry()
    async def update_session(self, session: PodcastSession) -> None:
        doc_ref = self._collection.document(session.session_id)
        await doc_ref.set(session.model_dump(mode="json"), merge=True)
        logger.info(
            "podcast_session_updated",
            session_id=session.session_id,
            state=session.workflow_state,
        )

    @with_provider_retry()
    async def list_sessions(self, *, limit: int = 50) -> list[PodcastSession]:
        query = self._collection.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        ).limit(limit)
        docs = query.stream()
        sessions = []
        async for doc in docs:
            sessions.append(PodcastSession.model_validate(doc.to_dict()))
        return sessions
