"""
Mash Voice - Configuration Management
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    # Meta/WhatsApp Business API Configuration
    whatsapp_access_token: str = Field(default="", description="WhatsApp permanent access token")
    whatsapp_phone_number_id: str = Field(default="", description="WhatsApp Phone Number ID")
    whatsapp_business_account_id: str = Field(default="", description="WhatsApp Business Account ID")
    whatsapp_verify_token: str = Field(default="", description="Webhook verification token")
    whatsapp_app_secret: str = Field(default="", description="App secret for signature verification")

    # Deepgram Configuration
    deepgram_api_key: str = Field(default="", description="Deepgram API Key")

    # Google Gemini Configuration
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini Model")

    # Redis Configuration
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0", description="Redis URL"
    )

    # Database Configuration
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/mash_voice",
        description="PostgreSQL URL",
    )

    # Security
    secret_key: str = Field(default="change-me-in-production", description="Secret key")
    api_key: str = Field(default="", description="API key for external access")

    # Feature Flags
    enable_message_logging: bool = Field(default=True)
    enable_agent_transfer: bool = Field(default=True)

    # Customer Service Configuration
    cs_default_agent: str = Field(default="customer_service_agent", description="Default agent for customer service")
    cs_knowledge_base_path: str = Field(default="", description="Path to custom knowledge base JSON")
    cs_escalation_enabled: bool = Field(default=True, description="Enable escalation to human agents")
    cs_max_turns_before_escalation: int = Field(default=10, description="Max turns before suggesting human help")
    cs_sentiment_detection: bool = Field(default=True, description="Enable sentiment/frustration detection")

    # Timeouts and Limits
    llm_timeout_seconds: float = Field(default=30.0, description="LLM timeout")
    max_conversation_duration_seconds: int = Field(default=3600, description="Max conversation duration")

    @property
    def redis_url_str(self) -> str:
        return str(self.redis_url)

    @property
    def database_url_str(self) -> str:
        return str(self.database_url)

    @property
    def whatsapp_api_url(self) -> str:
        """Get the WhatsApp Cloud API URL."""
        return f"https://graph.facebook.com/v18.0/{self.whatsapp_phone_number_id}/messages"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
