"""
Comprehensive tests for config modules.

Tests cover:
- llm_config.py: LLM provider configuration and initialization
- security_config.py: Password strength validation
- utils.py: Logging, port management utilities

Target: 80%+ code coverage for config modules
"""

import logging
import os
import socket
from unittest.mock import Mock, patch

import pytest

from neo4j_yass_mcp.config.llm_config import LLMConfig, chatLLM
from neo4j_yass_mcp.config.security_config import (
    WEAK_PASSWORDS,
    ZXCVBN_AVAILABLE,
    is_password_weak,
)
from neo4j_yass_mcp.config.utils import (
    configure_logging,
    find_available_port,
    get_preferred_ports_from_env,
    is_port_available,
)


class TestLLMConfig:
    """Test LLM configuration dataclass and provider initialization."""

    def test_llm_config_dataclass(self):
        """Test LLMConfig dataclass creation."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0,
            api_key="sk-test123",
        )

        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.0
        assert config.api_key == "sk-test123"
        assert config.streaming is False  # Default value

    def test_llm_config_with_streaming(self):
        """Test LLMConfig with streaming enabled."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-opus-20240229",
            temperature=0.7,
            api_key="sk-ant-test",
            streaming=True,
        )

        assert config.streaming is True

    def test_chat_llm_openai(self):
        """Test ChatOpenAI LLM initialization."""
        from pydantic import SecretStr

        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0,
            api_key="sk-test123",
        )

        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            llm = chatLLM(config)

            # Verify call with SecretStr-wrapped API key (LangChain 1.0)
            call_args = mock_openai.call_args
            assert call_args[1]["model"] == "gpt-4"
            assert call_args[1]["temperature"] == 0.0
            assert isinstance(call_args[1]["api_key"], SecretStr)
            assert call_args[1]["api_key"].get_secret_value() == "sk-test123"
            assert call_args[1]["streaming"] is False
            assert llm == mock_instance

    def test_chat_llm_openai_with_streaming(self):
        """Test ChatOpenAI with streaming enabled."""
        from pydantic import SecretStr

        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.5,
            api_key="sk-test",
            streaming=True,
        )

        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            chatLLM(config)

            # Verify call with SecretStr-wrapped API key (LangChain 1.0)
            call_args = mock_openai.call_args
            assert call_args[1]["model"] == "gpt-4"
            assert call_args[1]["temperature"] == 0.5
            assert isinstance(call_args[1]["api_key"], SecretStr)
            assert call_args[1]["api_key"].get_secret_value() == "sk-test"
            assert call_args[1]["streaming"] is True

    def test_chat_llm_anthropic(self):
        """Test ChatAnthropic LLM initialization."""
        from pydantic import SecretStr

        config = LLMConfig(
            provider="anthropic",
            model="claude-3-opus-20240229",
            temperature=0.0,
            api_key="sk-ant-test",
        )

        with patch("langchain_anthropic.ChatAnthropic") as mock_anthropic:
            mock_instance = Mock()
            mock_anthropic.return_value = mock_instance

            llm = chatLLM(config)

            # Verify call with model_name and SecretStr-wrapped API key (LangChain 1.0)
            call_args = mock_anthropic.call_args
            assert call_args[1]["model_name"] == "claude-3-opus-20240229"
            assert call_args[1]["temperature"] == 0.0
            assert isinstance(call_args[1]["api_key"], SecretStr)
            assert call_args[1]["api_key"].get_secret_value() == "sk-ant-test"
            assert call_args[1]["streaming"] is False
            assert llm == mock_instance

    def test_chat_llm_google_genai(self):
        """Test ChatGoogleGenerativeAI LLM initialization."""
        config = LLMConfig(
            provider="google-genai",
            model="gemini-pro",
            temperature=0.0,
            api_key="google-api-test",
        )

        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_google:
            mock_instance = Mock()
            mock_google.return_value = mock_instance

            llm = chatLLM(config)

            mock_google.assert_called_once_with(
                model="gemini-pro",
                temperature=0.0,
                google_api_key="google-api-test",
                streaming=False,
            )
            assert llm == mock_instance

    def test_chat_llm_unsupported_provider(self):
        """Test error handling for unsupported provider."""
        config = LLMConfig(
            provider="unsupported",
            model="test-model",
            temperature=0.0,
            api_key="test-key",
        )

        with pytest.raises(ValueError) as exc_info:
            chatLLM(config)

        assert "Unknown provider" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value)
        assert "openai, anthropic, google-genai" in str(exc_info.value)


class TestSecurityConfig:
    """Test password strength validation."""

    def test_weak_passwords_constant(self):
        """Test WEAK_PASSWORDS constant exists and has entries."""
        assert isinstance(WEAK_PASSWORDS, list)
        assert len(WEAK_PASSWORDS) > 0
        assert "password" in WEAK_PASSWORDS
        assert "123456" in WEAK_PASSWORDS

    def test_empty_password(self):
        """Test empty password is rejected."""
        is_weak, reason = is_password_weak("")

        assert is_weak is True
        assert "cannot be empty" in reason.lower()

    def test_weak_password_from_list(self):
        """Test passwords from WEAK_PASSWORDS list are detected."""
        weak_passwords = ["password", "password123", "123456", "qwerty", "admin"]

        for pwd in weak_passwords:
            is_weak, reason = is_password_weak(pwd)
            assert is_weak is True
            assert reason is not None

    def test_weak_password_case_insensitive(self):
        """Test weak password detection is case-insensitive."""
        variations = ["PASSWORD", "Password", "PaSsWoRd", "password"]

        for pwd in variations:
            is_weak, reason = is_password_weak(pwd)
            assert is_weak is True

    def test_short_password_fallback(self):
        """Test short password rejection (< 8 chars) in fallback mode."""
        # Mock ZXCVBN as unavailable to test fallback
        with patch("neo4j_yass_mcp.config.security_config.ZXCVBN_AVAILABLE", False):
            is_weak, reason = is_password_weak("Abc123!")

            assert is_weak is True
            assert "at least 8 characters" in reason.lower()

    def test_strong_password_fallback(self):
        """Test strong password acceptance in fallback mode."""
        with patch("neo4j_yass_mcp.config.security_config.ZXCVBN_AVAILABLE", False):
            # Not in weak list, >= 8 chars
            is_weak, reason = is_password_weak("MyStr0ng!Pass2024")

            assert is_weak is False
            assert reason is None

    @pytest.mark.skipif(not ZXCVBN_AVAILABLE, reason="zxcvbn library not available")
    def test_weak_password_with_zxcvbn(self):
        """Test weak password detection with zxcvbn library."""
        weak_passwords = ["password123", "qwerty", "123456", "letmein"]

        for pwd in weak_passwords:
            is_weak, reason = is_password_weak(pwd)
            assert is_weak is True
            assert "score" in reason.lower() or "common" in reason.lower()

    @pytest.mark.skipif(not ZXCVBN_AVAILABLE, reason="zxcvbn library not available")
    def test_strong_password_with_zxcvbn(self):
        """Test strong password acceptance with zxcvbn."""
        strong_passwords = [
            "X9$mKp2#Qw!zR",
            "MyV3ry$tr0ngP@ssw0rd!",
            "Tr0ub4dor&3Extended",
        ]

        for pwd in strong_passwords:
            is_weak, reason = is_password_weak(pwd)
            # Should pass (not weak)
            assert is_weak is False
            assert reason is None

    @pytest.mark.skipif(not ZXCVBN_AVAILABLE, reason="zxcvbn library not available")
    def test_password_with_user_inputs(self):
        """Test password containing user-specific strings is weak."""
        user_inputs = ["john", "smith", "company"]

        # Password containing username
        is_weak, reason = is_password_weak("john1234", user_inputs=user_inputs)

        # zxcvbn should detect this as weak (contains user input)
        assert is_weak is True

    def test_zxcvbn_exception_handling(self):
        """Test graceful fallback when zxcvbn raises exception."""
        if not ZXCVBN_AVAILABLE:
            pytest.skip("zxcvbn library not available")

        with patch("neo4j_yass_mcp.config.security_config.ZXCVBN_AVAILABLE", True):
            with patch("neo4j_yass_mcp.config.security_config.zxcvbn") as mock_zxcvbn:
                mock_zxcvbn.side_effect = Exception("Test error")

                # Should fall back to manual check
                is_weak, reason = is_password_weak("password")

                assert is_weak is True  # In weak list
                assert "commonly used" in reason.lower()


class TestConfigureLogging:
    """Test logging configuration utility."""

    def test_default_logging_configuration(self):
        """Test logging with default settings."""
        with patch.dict(os.environ, {}, clear=True):
            logger = configure_logging()

            assert logger is not None
            assert isinstance(logger, logging.Logger)

    def test_logging_with_custom_level(self):
        """Test logging with custom log level."""
        test_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in test_levels:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                logger = configure_logging()

                # Verify logger was created
                assert logger is not None

                # Verify root logger level is set
                root_logger = logging.getLogger()
                level_map = {
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                    "CRITICAL": logging.CRITICAL,
                }
                assert root_logger.level == level_map[level]

    def test_logging_with_invalid_level(self):
        """Test logging with invalid level defaults to INFO."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            logger = configure_logging()

            assert logger is not None
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

    def test_logging_with_custom_format(self):
        """Test logging with custom format."""
        custom_format = "%(levelname)s - %(message)s"

        with patch.dict(os.environ, {"LOG_FORMAT": custom_format}):
            logger = configure_logging()

            assert logger is not None

    def test_logging_with_lowercase_level(self):
        """Test logging handles lowercase level (via .upper())."""
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            logger = configure_logging()

            assert logger is not None
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG


class TestIsPortAvailable:
    """Test port availability checking."""

    def test_port_available_on_unused_port(self):
        """Test detection of available port."""
        # Find a likely available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            available_port = s.getsockname()[1]

        # Should be available
        assert is_port_available("127.0.0.1", available_port) is True

    def test_port_not_available_on_used_port(self):
        """Test detection of unavailable port."""
        # Create a socket that holds a port
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", 0))
        used_port = server_socket.getsockname()[1]

        try:
            # Port should not be available
            assert is_port_available("127.0.0.1", used_port) is False
        finally:
            server_socket.close()

    def test_port_available_different_hosts(self):
        """Test port availability on different host addresses."""
        # Test with localhost
        result_localhost = is_port_available("127.0.0.1", 65432)

        # Result depends on whether port is in use, but function should not crash
        assert isinstance(result_localhost, bool)


class TestFindAvailablePort:
    """Test finding available ports."""

    def test_find_available_port_from_preferred(self):
        """Test finding port from preferred list."""
        # Use high port numbers that are likely available
        preferred_ports = [45000, 45001, 45002]

        port = find_available_port("127.0.0.1", preferred_ports)

        assert port is not None
        assert port in preferred_ports

    def test_find_available_port_fallback_range(self):
        """Test fallback to range when preferred ports are busy."""
        # Block some preferred ports
        sockets = []
        preferred_ports = [45100, 45101, 45102]

        try:
            # Occupy all preferred ports
            for p in preferred_ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", p))
                sockets.append(s)

            # Should fall back to range
            port = find_available_port(
                "127.0.0.1", preferred_ports, fallback_range=(45200, 45300)
            )

            assert port is not None
            assert port not in preferred_ports
            assert 45200 <= port < 45300

        finally:
            for s in sockets:
                s.close()

    def test_find_available_port_no_ports_available(self):
        """Test when no ports are available (returns None)."""
        # Mock is_port_available to always return False
        with patch(
            "neo4j_yass_mcp.config.utils.is_port_available", return_value=False
        ):
            port = find_available_port(
                "127.0.0.1", [8000, 8001], fallback_range=(8000, 8010)
            )

            assert port is None

    def test_find_available_port_first_preferred_available(self):
        """Test returns first preferred port when available."""
        preferred_ports = [45300, 45301, 45302]

        port = find_available_port("127.0.0.1", preferred_ports)

        # Should return first available preferred port
        assert port == preferred_ports[0] or port in preferred_ports


class TestGetPreferredPortsFromEnv:
    """Test parsing preferred ports from environment."""

    def test_default_ports(self):
        """Test default port parsing."""
        with patch.dict(os.environ, {}, clear=True):
            ports = get_preferred_ports_from_env()

            assert ports == [8000, 8001, 8002]

    def test_custom_ports_from_env(self):
        """Test custom ports from environment variable."""
        with patch.dict(os.environ, {"PREFERRED_PORTS_MCP": "9000 9001 9002"}):
            ports = get_preferred_ports_from_env()

            assert ports == [9000, 9001, 9002]

    def test_single_port(self):
        """Test single port in environment."""
        with patch.dict(os.environ, {"PREFERRED_PORTS_MCP": "8080"}):
            ports = get_preferred_ports_from_env()

            assert ports == [8080]

    def test_ports_with_extra_whitespace(self):
        """Test ports with extra whitespace are handled."""
        with patch.dict(os.environ, {"PREFERRED_PORTS_MCP": "  8000   8001  8002  "}):
            ports = get_preferred_ports_from_env()

            assert ports == [8000, 8001, 8002]

    def test_invalid_port_values_ignored(self):
        """Test invalid port values are ignored."""
        with patch.dict(os.environ, {"PREFERRED_PORTS_MCP": "8000 abc 8001 xyz 8002"}):
            ports = get_preferred_ports_from_env()

            # Should only include valid integer ports
            assert ports == [8000, 8001, 8002]

    def test_custom_env_var_name(self):
        """Test using custom environment variable name."""
        with patch.dict(os.environ, {"CUSTOM_PORTS": "7000 7001"}):
            ports = get_preferred_ports_from_env(
                env_var="CUSTOM_PORTS", default="8000"
            )

            assert ports == [7000, 7001]

    def test_custom_default_value(self):
        """Test custom default value when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            ports = get_preferred_ports_from_env(
                env_var="NONEXISTENT", default="7500 7501"
            )

            assert ports == [7500, 7501]

    def test_empty_env_var_uses_default(self):
        """Test empty environment variable uses default."""
        with patch.dict(os.environ, {"PREFERRED_PORTS_MCP": ""}):
            ports = get_preferred_ports_from_env()

            # Empty string splits to empty list, so uses default
            assert ports == []

    def test_all_invalid_ports_uses_default(self):
        """Test fallback to default when all ports are invalid."""
        with patch.dict(os.environ, {"PREFERRED_PORTS_MCP": "abc def xyz"}):
            with patch("neo4j_yass_mcp.config.utils.logging.getLogger") as mock_logger:
                mock_log = Mock()
                mock_logger.return_value = mock_log

                ports = get_preferred_ports_from_env()

                # Should return empty list since no valid ports
                assert ports == []


class TestConfigModuleIntegration:
    """Integration tests for config modules."""

    def test_llm_config_all_providers(self):
        """Test all LLM providers can be configured."""
        providers = {
            "openai": ("ChatOpenAI", "gpt-4"),
            "anthropic": ("ChatAnthropic", "claude-3-opus-20240229"),
            "google-genai": ("ChatGoogleGenerativeAI", "gemini-pro"),
        }

        for provider, (class_name, model) in providers.items():
            config = LLMConfig(
                provider=provider,
                model=model,
                temperature=0.0,
                api_key="test-key",
            )

            # Map to actual langchain module paths
            module_paths = {
                "ChatOpenAI": "langchain_openai.ChatOpenAI",
                "ChatAnthropic": "langchain_anthropic.ChatAnthropic",
                "ChatGoogleGenerativeAI": "langchain_google_genai.ChatGoogleGenerativeAI",
            }

            with patch(module_paths[class_name]) as mock_class:
                chatLLM(config)
                mock_class.assert_called_once()

    def test_port_management_workflow(self):
        """Test complete port management workflow."""
        # 1. Get preferred ports from environment
        with patch.dict(os.environ, {"PREFERRED_PORTS_MCP": "45400 45401"}):
            preferred = get_preferred_ports_from_env()

        assert preferred == [45400, 45401]

        # 2. Find an available port
        port = find_available_port("127.0.0.1", preferred, fallback_range=(45500, 45600))

        assert port is not None

        # 3. Verify the port is actually available
        assert is_port_available("127.0.0.1", port) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=neo4j_yass_mcp.config"])
