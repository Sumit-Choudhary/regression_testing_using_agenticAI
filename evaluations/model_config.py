"""
DeepEval Model Provider Configuration
-------------------------------------
This module implements a custom Large Language Model (LLM) wrapper 
specifically designed for the DeepEval framework. It integrates 
Google's Gemini models via LangChain to serve as a 'Judge' for 
automated QA metrics and performance evaluation.
"""

import os
from typing import Optional, Any
from dotenv import load_dotenv
from deepeval.models import DeepEvalBaseLLM
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env file for secure API key management
load_dotenv()

class GeminiJudge(DeepEvalBaseLLM):
    """
    Custom LLM implementation for DeepEval using Google Gemini.
    
    This class bridges the LangChain ChatGoogleGenerativeAI model with the 
    DeepEvalBaseLLM interface, enabling the use of Gemini for G-Eval metrics, 
    Faithfulness, and other LLM-as-a-Judge evaluations.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """
        Initializes the Gemini Judge with the specified model configuration.

        Args:
            model_name (str): The identifier for the Gemini model version.
        
        Raises:
            ValueError: If the GOOGLE_API_KEY is not detected in the environment.
        """
        self.model_name = model_name
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("[CONFIGURATION ERROR]: GOOGLE_API_KEY not found in environment.")
        
        # Initialize the LangChain chat model instance
        self.model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key
        )

    def load_model(self) -> ChatGoogleGenerativeAI:
        """
        Retrieves the underlying LangChain model object.
        Required by the DeepEvalBaseLLM abstract class.

        Returns:
            ChatGoogleGenerativeAI: The active model instance.
        """
        return self.model

    def generate(self, prompt: str, schema: Optional[Any] = None) -> str:
        """
        Performs a synchronous generation request to the LLM.
        
        Note: As of the 2026 DeepEval specification, the 'schema' parameter 
        is available for structured output. This implementation returns 
        the raw string content for standard evaluation metrics.

        Args:
            prompt (str): The input text/rubric for the judge.
            schema (Optional[Any]): Structured output schema (if applicable).

        Returns:
            str: The generated textual response from the model.
        """
        chat_model = self.load_model()
        # Execution of the synchronous invoke call
        res = chat_model.invoke(prompt)
        return str(res.content)

    async def a_generate(self, prompt: str, schema: Optional[Any] = None) -> str:
        """
        Performs an asynchronous generation request to the LLM.
        Optimized for concurrent evaluation of multiple test cases.

        Args:
            prompt (str): The input text/rubric for the judge.
            schema (Optional[Any]): Structured output schema (if applicable).

        Returns:
            str: The generated textual response from the model.
        """
        chat_model = self.load_model()
        # Execution of the asynchronous invoke call
        res = await chat_model.ainvoke(prompt)
        return str(res.content)

    def get_model_name(self) -> str:
        """
        Returns the identifier of the model currently in use.
        Required for DeepEval reporting and metadata logging.

        Returns:
            str: The model name string.
        """
        return self.model_name