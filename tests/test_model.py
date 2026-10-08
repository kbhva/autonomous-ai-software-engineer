from types import SimpleNamespace

from flagship.model import OpenAIResponsesModel


def test_model_adapter_parses_function_call_without_api_key():
    item = SimpleNamespace(type="function_call", name="repository_action", call_id="call-1",
                           arguments='{"action":"list_files"}')
    response = SimpleNamespace(output=[item], output_text="")
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: response))
    decision = OpenAIResponsesModel(model="mock-model", client=client).next_action("inspect", [])
    assert decision.tool_call.name == "repository_action"
    assert decision.tool_call.arguments == {"action": "list_files"}


def test_model_adapter_returns_completion():
    response = SimpleNamespace(output=[], output_text="Done")
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: response))
    decision = OpenAIResponsesModel(client=client).next_action("task", [])
    assert decision.complete
    assert decision.message == "Done"


def test_model_adapter_accumulates_reported_token_usage_without_changing_decision():
    response = SimpleNamespace(output=[], output_text="Done",
                               usage=SimpleNamespace(input_tokens=11, output_tokens=7, total_tokens=18))
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: response))
    model = OpenAIResponsesModel(client=client)
    decision = model.next_action("task", [])
    assert decision.complete and decision.message == "Done"
    assert (model.input_tokens, model.output_tokens, model.total_tokens) == (11, 7, 18)
    assert model.usage_available
