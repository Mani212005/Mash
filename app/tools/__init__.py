"""
Mash Voice - Tools Package
"""

from app.tools.base_tool import BaseTool, ToolRegistry, ToolResult, get_tool_registry
from app.tools.implementations import (
    BookAppointmentTool,
    CancelAppointmentTool,
    CheckAvailabilityTool,
    CreateLeadTool,
    CreateSupportTicketTool,
    GetBusinessHoursTool,
    GetCompanyInfoTool,
    GetProductInfoTool,
    LookupCustomerTool,
    TransferToHumanTool,
    AddCallNotesTool,
    register_all_tools,
)
from app.tools.customer_service_tools import (
    LookupOrderTool,
    CheckRefundStatusTool,
    CreateSupportTicketTool as CSCreateSupportTicketTool,
    GetTicketStatusTool,
    EscalateToHumanTool,
    SearchKnowledgeBaseTool,
    GetBusinessHoursTool as CSGetBusinessHoursTool,
    InitiateRefundTool,
    CUSTOMER_SERVICE_TOOLS,
    register_customer_service_tools,
)

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "get_tool_registry",
    "register_all_tools",
    "CheckAvailabilityTool",
    "BookAppointmentTool",
    "CancelAppointmentTool",
    "CreateSupportTicketTool",
    "LookupCustomerTool",
    "GetBusinessHoursTool",
    "GetCompanyInfoTool",
    "GetProductInfoTool",
    "CreateLeadTool",
    "TransferToHumanTool",
    "AddCallNotesTool",
    # Customer Service Tools
    "LookupOrderTool",
    "CheckRefundStatusTool",
    "GetTicketStatusTool",
    "EscalateToHumanTool",
    "SearchKnowledgeBaseTool",
    "InitiateRefundTool",
    "CUSTOMER_SERVICE_TOOLS",
    "register_customer_service_tools",
]
