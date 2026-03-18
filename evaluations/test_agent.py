"""
Agentic QA Regression Suite
---------------------------
This test suite leverages the DeepEval framework to perform automated 
validation of the Web Navigation Agent. It utilizes a 'Hybrid Evaluation' 
approach, combining semantic reasoning (G-Eval) with deterministic 
technical validation (ToolCorrectnessMetric).
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall
from deepeval.metrics import GEval, ToolCorrectnessMetric
from evaluations.model_config import GeminiJudge

# --- SHARED FIXTURES ---

@pytest.fixture
def gemini_judge():
    return GeminiJudge()

@pytest.fixture
def login_metric(gemini_judge):
    return GEval(
        name="Login Success",
        evaluation_steps=[
            "Check if 'standard_user' (exact value) was typed into #user-name. Fail if any other username was used.",
            "Check if 'secret_sauce' was typed into #password.",
            "Check if #login-button was clicked after both fields were filled.",
            "Check if the final URL contains 'inventory.html'.",
            "Score 0 if wrong credentials were used, even if the URL shows success.",
            "Only score above 0.7 if ALL four conditions above are met."
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=gemini_judge,
        threshold=0.7
    )

@pytest.fixture
def tool_metric(gemini_judge):
    return ToolCorrectnessMetric(
        threshold=0.7,
        model=gemini_judge,
        should_consider_ordering=True
    )

# Ground truth tool sequence — shared across passing and failing tests
EXPECTED_TOOLS = [
    ToolCall(name="type_text", input_parameters={"selector": "#user-name", "value": "standard_user"}),
    ToolCall(name="type_text", input_parameters={"selector": "#password", "value": "secret_sauce"}),
    ToolCall(name="click_element", input_parameters={"selector": "#login-button"})
]


# --- TEST CASES ---

@pytest.mark.asyncio
async def test_login_success(login_metric, tool_metric):
    """
    PASSING CASE: Agent uses correct credentials and reaches inventory page.
    This test should PASS.
    """
    test_case = LLMTestCase(
        input="Login to SauceDemo with standard_user",
        actual_output="""
            1. Typed 'standard_user' into #user-name
            2. Typed 'secret_sauce' into #password
            3. Clicked #login-button
            4. Current URL is: https://www.saucedemo.com/inventory.html
        """,
        tools_called=[
            ToolCall(name="type_text", input_parameters={"selector": "#user-name", "value": "standard_user"}),
            ToolCall(name="type_text", input_parameters={"selector": "#password", "value": "secret_sauce"}),
            ToolCall(name="click_element", input_parameters={"selector": "#login-button"})
        ],
        expected_tools=EXPECTED_TOOLS,
        expected_output="Agent navigates to inventory page after entering valid credentials."
    )

    # ← This line was missing in the original — nothing was being evaluated without it
    assert_test(test_case, [login_metric, tool_metric])


@pytest.mark.asyncio
async def test_login_wrong_credentials(login_metric, tool_metric):
    """
    FAILING CASE: Agent uses wrong username. 
    This test should FAIL — verifies the metrics are actually catching errors.
    """
    test_case = LLMTestCase(
        input="Login to SauceDemo with standard_user",
        actual_output="""
            1. Typed 'standard_wrong_user' into #user-name
            2. Typed 'secret_sauce' into #password
            3. Clicked #login-button
            4. Current URL is: https://www.saucedemo.com/inventory.html
        """,
        tools_called=[
            ToolCall(name="type_text", input_parameters={"selector": "#user-name", "value": "standard_wrong_user"}),
            ToolCall(name="type_text", input_parameters={"selector": "#password", "value": "secret_sauce"}),
            ToolCall(name="click_element", input_parameters={"selector": "#login-button"})
        ],
        expected_tools=EXPECTED_TOOLS,
        expected_output="Agent navigates to inventory page after entering valid credentials."
    )

    assert_test(test_case, [login_metric, tool_metric])


@pytest.mark.asyncio
async def test_login_missing_password_step(login_metric, tool_metric):
    """
    FAILING CASE: Agent skips the password field entirely.
    This test should FAIL — catches incomplete tool sequences.
    """
    test_case = LLMTestCase(
        input="Login to SauceDemo with standard_user",
        actual_output="""
            1. Typed 'standard_user' into #user-name
            2. Clicked #login-button
            3. Current URL is: https://www.saucedemo.com/ (login failed)
        """,
        tools_called=[
            ToolCall(name="type_text", input_parameters={"selector": "#user-name", "value": "standard_user"}),
            ToolCall(name="click_element", input_parameters={"selector": "#login-button"})
            # password step deliberately missing
        ],
        expected_tools=EXPECTED_TOOLS,
        expected_output="Agent navigates to inventory page after entering valid credentials."
    )

    assert_test(test_case, [login_metric, tool_metric])