import logging
import asyncio
from typing import List
import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from models.config import settings

logger = logging.getLogger(__name__)

# Initialize Vertex AI
vertexai.init(project=settings.GCP_PROJECT, location=settings.VERTEX_LOCATION)

class AIService:
    def __init__(self, model_name: str = "text-embedding-004"):
        self.model_name = model_name
        self.model = None # Lazy load

    async def get_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """
        Generates an embedding for the given text using Vertex AI.
        Uses asyncio.to_thread to avoid blocking the event loop.
        """
        if self.model is None:
            logger.info("Initializing Vertex AI model (Lazy Loading)...")
            # Load model in a thread to avoid blocking startup
            self.model = await asyncio.to_thread(TextEmbeddingModel.from_pretrained, self.model_name)

        try:
            return await asyncio.to_thread(self._get_embedding_sync, text, task_type)
        except Exception as e:
            logger.error(f"Error fetching embedding from Vertex AI: {e}")
            raise

    def _get_embedding_sync(self, text: str, task_type: str) -> List[float]:
        inputs = [TextEmbeddingInput(text, task_type)]
        embeddings = self.model.get_embeddings(inputs)
        return embeddings[0].values

ai_service = AIService()
