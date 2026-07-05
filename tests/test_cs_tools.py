"""
Mash Voice - Customer Service Tools Tests
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.tools.customer_service_tools import (
    LookupOrderTool,
    CheckRefundStatusTool,
    CreateSupportTicketTool,
    GetTicketStatusTool,
    EscalateToHumanTool,
    SearchKnowledgeBaseTool,
    GetBusinessHoursTool,
    InitiateRefundTool,
)
from app.tools.base_tool import ToolResult


class TestLookupOrderTool:
    """Tests for LookupOrderTool."""

    @pytest.fixture
    def tool(self):
        return LookupOrderTool()

    @pytest.mark.asyncio
    async def test_lookup_by_order_id_success(self, tool):
        result = await tool.execute(order_id="ORD-12345")
        assert result.success
        assert result.data["id"] == "ORD-12345"
        assert result.data["status"] == "shipped"

    @pytest.mark.asyncio
    async def test_lookup_by_order_id_not_found(self, tool):
        result = await tool.execute(order_id="ORD-UNKNOWN")
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_lookup_by_phone_success(self, tool):
        result = await tool.execute(phone_number="+1234567890")
        assert result.success
        assert "orders" in result.data
        assert result.data["count"] > 0

    @pytest.mark.asyncio
    async def test_lookup_by_phone_not_found(self, tool):
        result = await tool.execute(phone_number="+9999999999")
        assert not result.success
        assert "no orders found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_lookup_missing_all_params(self, tool):
        result = await tool.execute()
        assert not result.success
        assert "either an order id or phone number" in result.error.lower()


class TestCheckRefundStatusTool:
    """Tests for CheckRefundStatusTool."""

    @pytest.fixture
    def tool(self):
        return CheckRefundStatusTool()

    @pytest.mark.asyncio
    async def test_check_refund_success(self, tool):
        result = await tool.execute(order_id="ORD-12345")
        assert result.success
        assert result.data["order_id"] == "ORD-12345"
        assert result.data["refund_status"] == "not_requested"

    @pytest.mark.asyncio
    async def test_check_refund_order_not_found(self, tool):
        result = await tool.execute(order_id="ORD-UNKNOWN")
        assert not result.success
        assert "not found" in result.error.lower()

    def test_validation_missing_required(self, tool):
        is_valid, error = tool.validate_params({})
        assert not is_valid
        assert "order_id" in error


class TestCreateSupportTicketTool:
    """Tests for CreateSupportTicketTool."""

    @pytest.fixture
    def tool(self):
        return CreateSupportTicketTool()

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, tool):
        result = await tool.execute(
            customer_phone="+1234567890",
            issue_type="order_issue",
            description="My package has not arrived.",
            priority="high",
            order_id="ORD-12345",
        )
        assert result.success
        assert result.data["id"].startswith("TKT-")
        assert result.data["status"] == "open"
        assert result.data["customer_phone"] == "+1234567890"

    def test_validation_missing_required(self, tool):
        is_valid, error = tool.validate_params(
            {"customer_phone": "+1234567890", "issue_type": "order_issue"}
        )
        assert not is_valid
        assert "description" in error


class TestGetTicketStatusTool:
    """Tests for GetTicketStatusTool."""

    @pytest.fixture
    def tool(self):
        return GetTicketStatusTool()

    @pytest.mark.asyncio
    async def test_get_ticket_status_not_found(self, tool):
        result = await tool.execute(ticket_id="TKT-UNKNOWN")
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_get_ticket_status_success(self, tool):
        # First create a ticket
        create_tool = CreateSupportTicketTool()
        create_res = await create_tool.execute(
            customer_phone="+1234567890",
            issue_type="order_issue",
            description="Testing ticket status",
        )
        ticket_id = create_res.data["id"]

        # Get the status
        result = await tool.execute(ticket_id=ticket_id)
        assert result.success
        assert result.data["id"] == ticket_id
        assert result.data["status"] == "open"


class TestEscalateToHumanTool:
    """Tests for EscalateToHumanTool."""

    @pytest.fixture
    def tool(self):
        return EscalateToHumanTool()

    @pytest.mark.asyncio
    async def test_escalation_success(self, tool):
        result = await tool.execute(
            reason="Customer wants to talk to manager",
            customer_phone="+1234567890",
            conversation_summary="Customer is upset about delayed order",
            priority="high",
        )
        assert result.success
        assert result.data["id"].startswith("ESC-")
        assert result.data["status"] == "pending"
        assert result.data["reason"] == "Customer wants to talk to manager"


class TestInitiateRefundTool:
    """Tests for InitiateRefundTool."""

    @pytest.fixture
    def tool(self):
        return InitiateRefundTool()

    @pytest.mark.asyncio
    async def test_initiate_refund_success(self, tool):
        result = await tool.execute(order_id="ORD-12345", reason="damaged")
        assert result.success
        assert result.data["id"].startswith("REF-")
        assert result.data["order_id"] == "ORD-12345"
        assert result.data["status"] == "pending_review"

    @pytest.mark.asyncio
    async def test_initiate_refund_order_not_found(self, tool):
        result = await tool.execute(order_id="ORD-UNKNOWN", reason="wrong_item")
        assert not result.success
        assert "not found" in result.error.lower()


class TestSearchKnowledgeBaseTool:
    """Tests for SearchKnowledgeBaseTool."""

    @pytest.fixture
    def tool(self):
        return SearchKnowledgeBaseTool()

    @pytest.mark.asyncio
    async def test_search_by_category(self, tool):
        mock_kb_service = MagicMock()
        mock_entry = MagicMock()
        mock_entry.to_dict.return_value = {"id": "1", "question": "Hours?", "answer": "9-5"}
        mock_kb_service.get_by_category.return_value = [mock_entry]

        with patch(
            "app.tools.customer_service_tools.get_knowledge_service", return_value=mock_kb_service
        ):
            result = await tool.execute(query="test", category="shipping")
            assert result.success
            assert result.data["category"] == "shipping"
            assert len(result.data["entries"]) == 1

    @pytest.mark.asyncio
    async def test_search_semantic(self, tool):
        mock_kb_service = MagicMock()
        mock_entry = MagicMock()
        mock_entry.to_dict.return_value = {"id": "2", "question": "Refund?", "answer": "30 days"}
        mock_kb_service.find_answer = AsyncMock(return_value=("30 days refund policy", mock_entry))

        with patch(
            "app.tools.customer_service_tools.get_knowledge_service", return_value=mock_kb_service
        ):
            result = await tool.execute(query="What is your refund policy?")
            assert result.success
            assert result.data["answer"] == "30 days refund policy"
            assert result.data["source"]["question"] == "Refund?"
