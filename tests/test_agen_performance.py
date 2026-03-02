from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric

def test_saucedemo_navigation():
    # 1. We define what 'Success' looks like
    input_goal = "Login and add a backpack to the cart."
    
    # 2. We pull the actual results from the Agent's final state
    # (In a real run, you'd import the result from your main.py execution)
    actual_output = "Agent logged in, found the backpack, and clicked 'Add to Cart'."
    retrieval_context = ["User reached /inventory.html", "Cart badge updated to 1"]

    # 3. Use DeepEval to see if the Agent's actions match the goal
    metric = AnswerRelevancyMetric(threshold=0.7)
    test_case = LLMTestCase(
        input=input_goal,
        actual_output=actual_output,
        retrieval_context=retrieval_context
    )

    assert_test(test_case, [metric])