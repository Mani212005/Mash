"""
Mash Voice - Tool Tests
"""

import pytest

from app.tools import (
    BaseTool,
    CheckAvailabilityTool,
    BookAppointmentTool,
    GetBusinessHoursTool,
    get_tool_registry,
    register_all_tools,
)


@pytest.fixture
def availability_tool():
    return CheckAvailabilityTool()


@pytest.fixture
def booking_tool():
    return BookAppointmentTool()


@pytest.fixture
def hours_tool():
    return GetBusinessHoursTool()


class TestCheckAvailabilityTool:
    """Tests for availability checking tool."""

    def test_tool_attributes(self, availability_tool):
        """Test tool has required attributes."""
        assert availability_tool.name == "check_availability"
        assert len(availability_tool.description) > 0
        assert "date" in availability_tool.parameters["properties"]

    @pytest.mark.asyncio
    async def test_check_valid_date(self, availability_tool):
        """Test checking availability for a valid date."""
        result = await availability_tool.execute(date="2026-02-15")
        assert result.success
        assert "date" in result.data
        assert "available_slots" in result.data

    @pytest.mark.asyncio
    async def test_check_invalid_date(self, availability_tool):
        """Test checking availability with invalid date format."""
        result = await availability_tool.execute(date="invalid-date")
        assert not result.success
        assert result.error is not None

    def test_validate_params_missing_required(self, availability_tool):
        """Test parameter validation with missing required field."""
        is_valid, error = availability_tool.validate_params({})
        assert not is_valid
        assert "date" in error


class TestBookAppointmentTool:
    """Tests for appointment booking tool."""

    def test_tool_attributes(self, booking_tool):
        """Test tool has required attributes."""
        assert booking_tool.name == "book_appointment"
        assert "date" in booking_tool.parameters["required"]
        assert "time" in booking_tool.parameters["required"]
        assert "customer_name" in booking_tool.parameters["required"]

    @pytest.mark.asyncio
    async def test_book_appointment(self, booking_tool):
        """Test booking an appointment."""
        result = await booking_tool.execute(
            date="2026-02-15",
            time="10:00",
            customer_name="John Doe",
            customer_phone="+1234567890",
        )
        assert result.success
        assert "confirmation_number" in result.data
        assert result.data["confirmation_number"].startswith("APT-")


class TestGetBusinessHoursTool:
    """Tests for business hours tool."""

    @pytest.mark.asyncio
    async def test_get_all_hours(self, hours_tool):
        """Test getting all business hours."""
        result = await hours_tool.execute()
        assert result.success
        assert "hours" in result.data

    @pytest.mark.asyncio
    async def test_get_specific_day(self, hours_tool):
        """Test getting hours for a specific day."""
        result = await hours_tool.execute(day="Monday")
        assert result.success
        assert result.data["day"] == "Monday"


class TestToolRegistry:
    """Tests for tool registry."""

    def test_register_and_get(self):
        """Test registering and retrieving tools."""
        registry = get_tool_registry()
        
        # Register all tools
        register_all_tools()
        
        # Check tools are registered
        assert registry.get("check_availability") is not None
        assert registry.get("book_appointment") is not None
        assert registry.get("create_support_ticket") is not None

    def test_list_tools(self):
        """Test listing registered tools."""
        registry = get_tool_registry()
        register_all_tools()
        
        tools = registry.list_tools()
        assert len(tools) > 0
        assert "check_availability" in tools

    def test_get_definitions(self):
        """Test getting tool definitions."""
        registry = get_tool_registry()
        register_all_tools()
        
        definitions = registry.get_definitions(["check_availability", "book_appointment"])
        assert len(definitions) == 2
        assert all("name" in d and "description" in d for d in definitions)
