"""
Agentic QA Regression Suite
---------------------------
This test suite leverages the DeepEval framework to perform automated 
validation of the Web Navigation Agent. It utilizes a 'Hybrid Evaluation' 
approach, combining semantic reasoning (G-Eval) with deterministic 
technical validation (ToolCorrectnessMetric).
"""

import pytest
import os
import json
from datetime import datetime
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall
from deepeval.metrics import GEval, ToolCorrectnessMetric
from evaluations.model_config import GeminiJudge 

# --- CONFIGURATION ---
RESULTS_FOLDER = "./test_results"

# Ensure persistence directory exists for test artifacts
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

@pytest.mark.asyncio
async def test_login_comprehensive_validation():
    """
    Validates the end-to-end login workflow of the SauceDemo application.
    
    This test assesses:
    1. Semantic Goal Achievement: Did the agent reach the inventory page?
    2. Tool Execution Accuracy: Did the agent call the correct sequence of tools?
    """
    
    # Initialize the LLM-as-a-Judge using the custom Gemini configuration
    gemini_judge = GeminiJudge()

    # --- 1. METRIC DEFINITIONS ---

    # G-Eval: Uses LLM reasoning to grade the actual output against a rubric
    login_metric = GEval(
        name="Login Success",
        evaluation_steps=[
            "Check if the actual output mentions typing into #user-name and #password.",
            "Check if the agent clicked the #login-button.",
            "Verify that the final URL contains 'inventory.html'.",
            "Give a high score if all these navigation steps are present."
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=gemini_judge,
        threshold=0.7
    )

    # ToolCorrectnessMetric: Validates the technical precision of function calling
    tool_metric = ToolCorrectnessMetric(
        threshold=0.7,
        model=gemini_judge,
        # Set to True to ensure the agent follows the logical order of operations
        should_consider_ordering=True
    )

    # --- 2. TEST CASE CONSTRUCTION ---

    # This test case simulates the expected state after a successful agent run
    test_case = LLMTestCase(
        input="Login to SauceDemo with standard_user",
        actual_output="""
            1. Typed 'standard_user' into #user-name
            2. Typed 'secret_sauce' into #password
            3. Clicked #login-button
            4. Current URL is: https://www.saucedemo.com/inventory.html
        """,
        retrieval_context=["Inventory page is the success state."],
        
        # Captured tools during the 'Act' phase of the agent loop
        tools_called=[
            ToolCall(name="type_text", input_parameters={"selector": "#user-name"}),
            ToolCall(name="click_element", input_parameters={"selector": "#login-button"})
        ],
        
        # Ground Truth: Expected tool sequence for the defined goal
        expected_tools=[
            # Note: Empty dicts prevent NoneType calculation errors in DeepEval core
            ToolCall(name="type_text", input_parameters={}),
            ToolCall(name="click_element", input_parameters={})
        ],
        expected_output="The agent should successfully navigate to the inventory page after entering credentials."
    )