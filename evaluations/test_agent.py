import pytest
import os
import pytest
import json
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall
from datetime import datetime
from deepeval.metrics import (
    GEval, 
    FaithfulnessMetric, 
    AnswerRelevancyMetric, 
    ToolCorrectnessMetric
)
from evaluations.model_config import GeminiJudge 

test_results_summary = {}

RESULTS_FOLDER = "./test_results"
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

@pytest.mark.asyncio
async def test_login_comprehensive_validation():
    gemini_judge = GeminiJudge()

    # 1. Metric Definitions
    login_metric = GEval(
        name="Login Success",
        # criteria="Determine if the agent reached the inventory dashboard.",
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

    tool_metric = ToolCorrectnessMetric(
        threshold=0.7,
        model=gemini_judge,
        # FIX: Explicitly tell DeepEval what to check to avoid None results
        # If you only want to check tool names, use this:
        should_consider_ordering=True
    )

    # 2. Unified Test Case
    test_case = LLMTestCase(
        # input="Login to SauceDemo",
        # actual_output="Logged in successfully.",
        input="Login to SauceDemo with standard_user",
        actual_output="""
        1. Typed 'standard_user' into #user-name
        2. Typed 'secret_sauce' into #password
        3. Clicked #login-button
        4. Current URL is: https://www.saucedemo.com/inventory.html
    """,
        retrieval_context=["Inventory page is the success state."],
        
        # FIX: Ensure both lists have matching structures
        tools_called=[
            ToolCall(name="type_text", input_parameters={"selector": "#user-name"}),
            ToolCall(name="click_element", input_parameters={"selector": "#login-button"})
        ],
        expected_tools=[
            # If you don't care about parameters here, still use an empty dict 
            # to prevent the 'NoneType' score calculation error
            ToolCall(name="type_text", input_parameters={}),
            ToolCall(name="click_element", input_parameters={})
        ],
        expected_output="The agent should successfully navigate to the inventory page after entering credentials."
    )

    # 3. Run assertion
    assert_test(test_case, [login_metric, tool_metric])

    # 3. MANUAL EXPORT (This fixes the blank folder issue)
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "test_input": test_case.input,
        "actual_output": test_case.actual_output,
        "score": login_metric.score,
        "reason": login_metric.reason,
        "success": login_metric.success
    }

    file_name = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(os.path.join(RESULTS_FOLDER, file_name), "w") as f:
        json.dump(result_data, f, indent=4)
    
    print(f"\n✅ Results manually saved to {RESULTS_FOLDER}/{file_name}")

