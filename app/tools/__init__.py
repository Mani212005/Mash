"""
Mash Voice - Tools Package
"""

from app.tools.base_tool import BaseTool, ToolRegistry, ToolResult, get_tool_registry
from app.tools.customer_service_tools import (
    CUSTOMER_SERVICE_TOOLS,
    CheckRefundStatusTool,
    EscalateToHumanTool,
    GetTicketStatusTool,
    InitiateRefundTool,
    LookupOrderTool,
    SearchKnowledgeBaseTool,
    register_customer_service_tools,
)
from app.tools.customer_service_tools import (
    CreateSupportTicketTool as CSCreateSupportTicketTool,
)
from app.tools.customer_service_tools import (
    GetBusinessHoursTool as CSGetBusinessHoursTool,
)
from app.tools.implementations import (
    AddCallNotesTool,
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
    register_all_tools,
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
