import os
from typing import Optional, Any
from dotenv import load_dotenv
from deepeval.models import DeepEvalBaseLLM
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

class GeminiJudge(DeepEvalBaseLLM):
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("❌ GOOGLE_API_KEY not found.")
        
        self.model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key
        )

    def load_model(self):
        """Mandatory: Returns the underlying model object."""
        return self.model

    def generate(self, prompt: str, schema: Optional[Any] = None) -> str:
        """Mandatory: Synchronous generation. 'schema' is now required by DeepEval 2026."""
        chat_model = self.load_model()
        # Note: If schema is provided, you'd usually use model.with_structured_output(schema)
        # But for basic G-Eval, we can return the raw string.
        res = chat_model.invoke(prompt)
        return res.content

    async def a_generate(self, prompt: str, schema: Optional[Any] = None) -> str:
        """Mandatory: Asynchronous generation."""
        chat_model = self.load_model()
        res = await chat_model.ainvoke(prompt)
        return res.content

    def get_model_name(self) -> str:
        """Mandatory: Returns the model name string."""
        return self.model_name