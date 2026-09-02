import asyncio

from fastapi import APIRouter, HTTPException, status

from app.schemas import ChatRequest, ChatResponse
from app.services.conversation import ConversationStore
from app.services.groq_chat import GroqChatError, generate_reply

router = APIRouter(prefix="/api", tags=["chat"])
conversation_store = ConversationStore()


# ==============================================================================
# PHASE 2: THE BRAIN (Main Chat Completion API Route)
# ==============================================================================
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    1. Validate request.text is non-blank (raise 422 HTTP error if empty).
    2. Retrieve conversation history from conversation_store.history(session_id).
    3. Call generate_reply() via asyncio.to_thread.
    4. Save the turn using conversation_store.append_turn().
    5. Return ChatResponse(sessionId, reply, turnsRetained).
    """
    user_text = request.text.strip()
    if not user_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message text cannot be empty.",
        )

    history = conversation_store.history(request.session_id)

    try:
        reply = await asyncio.to_thread(generate_reply, history, user_text)
    except GroqChatError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during chat completion: {exc}",
        ) from exc

    turns = conversation_store.append_turn(request.session_id, user_text, reply)

    return ChatResponse(
        sessionId=request.session_id,
        reply=reply,
        turnsRetained=turns,
    )
