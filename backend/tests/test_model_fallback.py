import pytest
from unittest.mock import MagicMock, patch
from google.genai.errors import APIError
from app.services.llm_manager import generate_chat_turn, get_ai_status

@pytest.mark.asyncio
async def test_automatic_model_fallback_on_404():
    # Mock GenAI client: first model throws 404 NOT_FOUND, second model succeeds
    mock_client = MagicMock()

    err_404 = Exception("404 NOT_FOUND: models/retired-model-1.5 is not found for API version v1beta")

    mock_chunk = MagicMock()
    mock_chunk.text = "Hello! I am answering via fallback model."
    mock_chunk.candidates = []

    mock_chat = MagicMock()
    mock_chat.send_message_stream.return_value = [mock_chunk]

    def create_chat_side_effect(*args, **kwargs):
        model_name = kwargs.get("model") or (args[0] if args else "")
        if "1.5" in str(model_name) or "retired" in str(model_name):
            raise err_404
        return mock_chat

    mock_client.chats.create.side_effect = create_chat_side_effect

    with patch("app.services.llm_manager.get_genai_client", return_value=mock_client), \
         patch("app.services.llm_manager.resolve_working_model", return_value=("retired-model-1.5", False)):
        tokens = []
        source = None
        used_model = None

        async for item in generate_chat_turn(
            query="Hello",
            history=[],
            db=None,
            model_override="retired-model-1.5",
        ):
            if item.get("event") == "token":
                tokens.append(item.get("data", {}).get("text", ""))
            elif item.get("event") == "done":
                source = item.get("data", {}).get("source")
                used_model = item.get("data", {}).get("model")

        full_output = "".join(tokens)
        assert len(full_output) > 0
        assert source == "gemini"
        assert "retired" not in (used_model or "")

