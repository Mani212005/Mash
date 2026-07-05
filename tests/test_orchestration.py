import pytest
from app.services.agent_service import get_orchestrator
from app.models.schemas import Message, ChannelType, CallContext
from app.core.state import get_state_manager

@pytest.mark.asyncio
async def test_handle_message_whatsapp():
    orchestrator = get_orchestrator()
    state_manager = get_state_manager()
    
    # Initialize the state to use support_agent
    session_id = "wa_test_chat_1"
    await state_manager.set_state(session_id, {
        "phone_number": "test_sender_1",
        "messages": [],
        "current_agent": "support_agent",
        "context": {},
    })
    
    message = Message(
        message_id="test_msg_1",
        chat_id="test_chat_1",
        sender_id="test_sender_1",
        channel=ChannelType.WHATSAPP,
        text="Hello, I want to talk to human",
        is_bot=False,
    )
    
    # Process
    res = await orchestrator.handle_message(message)
    # The SupportAgent should escalate immediately because of "talk to human"
    assert res.transfer_to == "human_handoff_agent"
    assert "transfer" in res.message.lower() or "connect" in res.message.lower() or "hold" in res.message.lower()


@pytest.mark.asyncio
async def test_panel_mode_not_implemented():
    orchestrator = get_orchestrator()
    state_manager = get_state_manager()
    
    # Create call state with panel mode
    session_id = "wa_test_panel_1"
    context = CallContext(
        channel_session_id=session_id,
        current_agent_id="primary_agent",
        chat_mode="panel"
    )
    await state_manager.update_call_context(session_id, context)
    
    # Process message and expect NotImplementedError
    message = Message(
        message_id="test_msg_panel",
        chat_id="test_panel_1",
        sender_id="test_sender_panel",
        channel=ChannelType.WHATSAPP,
        text="Hello",
        is_bot=False,
    )
    
    with pytest.raises(NotImplementedError):
        await orchestrator.handle_message(message)
        
    # Clean up state
    await state_manager.delete_call_state(session_id)
