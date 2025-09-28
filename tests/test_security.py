"""
Test Security Implementation

Comprehensive tests for the security module implementation.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path before importing modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from security import (  # noqa: E402
    APIKeyValidationResult,
    APIKeyValidator,
    LocalEncryptedSecretsManager,
    PermissionLevel,
    SafetyStatus,
    SecretBackend,
    SecretsConfigManager,
    SecretsManagerFactory,
    SecurityManager,
)


class TestAPIKeyValidator:
    """Test API key validator functionality."""

    def test_validation_result_creation(self):
        """Test APIKeyValidationResult creation."""
        result = APIKeyValidationResult(
            is_safe=True,
            safety_status=SafetyStatus.SAFE,
            permission_level=PermissionLevel.TRADING_ONLY,
            warnings=["Test warning"],
            errors=[],
            withdrawal_addresses=[],
            ip_whitelist=["192.168.1.1"],
            restrictions={},
        )

        assert result.is_safe is True
        assert result.safety_status == SafetyStatus.SAFE
        assert result.permission_level == PermissionLevel.TRADING_ONLY
        assert len(result.warnings) == 1
        assert len(result.errors) == 0

    @patch("security.api_key_validator.ccxt")
    def test_validator_initialization(self, mock_ccxt):
        """Test validator initialization."""
        mock_exchange = Mock()
        mock_ccxt.binance.return_value = mock_exchange

        validator = APIKeyValidator("binance", "test_key", "test_secret")

        assert validator.exchange_name == "binance"
        assert validator.api_key == "test_key"
        assert validator.secret == "test_secret"
        mock_ccxt.binance.assert_called_once()

    def test_safety_status_determination(self):
        """Test safety status determination logic."""
        validator = APIKeyValidator("binance", "test_key", "test_secret")

        # Test critical status (withdrawal enabled)
        status = validator._determine_safety_status(
            PermissionLevel.WITHDRAWAL_ENABLED, True, ["192.168.1.1"]
        )
        assert status == SafetyStatus.CRITICAL

        # Test unsafe status (full access)
        status = validator._determine_safety_status(
            PermissionLevel.FULL_ACCESS, False, ["192.168.1.1"]
        )
        assert status == SafetyStatus.UNSAFE

        # Test warning status (no IP whitelist)
        status = validator._determine_safety_status(PermissionLevel.TRADING_ONLY, False, [])
        assert status == SafetyStatus.WARNING

        # Test safe status
        status = validator._determine_safety_status(
            PermissionLevel.TRADING_ONLY, False, ["192.168.1.1"]
        )
        assert status == SafetyStatus.SAFE


class TestSecretsManager:
    """Test secrets management functionality."""

    def test_local_encrypted_manager_creation(self):
        """Test local encrypted secrets manager creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = LocalEncryptedSecretsManager("test_password", temp_dir)

            assert manager.storage_path == Path(temp_dir)
            assert manager.cipher is not None

    def test_secret_storage_and_retrieval(self):
        """Test storing and retrieving secrets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = LocalEncryptedSecretsManager("test_password", temp_dir)

            # Store a secret
            success = manager.set_secret("test_key", "test_value")
            assert success is True

            # Retrieve the secret
            value = manager.get_secret("test_key")
            assert value == "test_value"

    def test_secret_deletion(self):
        """Test secret deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = LocalEncryptedSecretsManager("test_password", temp_dir)

            # Store a secret
            manager.set_secret("test_key", "test_value")

            # Delete the secret
            success = manager.delete_secret("test_key")
            assert success is True

            # Verify deletion
            value = manager.get_secret("test_key")
            assert value is None

    def test_secrets_factory(self):
        """Test secrets manager factory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SecretsManagerFactory.create_secrets_manager(
                SecretBackend.LOCAL_ENCRYPTED,
                master_password="test_password",
                storage_path=temp_dir,
            )

            assert isinstance(manager, LocalEncryptedSecretsManager)


class TestSecretsConfigManager:
    """Test secrets configuration manager."""

    def test_config_manager_initialization(self):
        """Test secrets config manager initialization."""
        mock_config_manager = Mock()
        mock_config_manager.load_full_config.return_value = {
            "secrets": {
                "backend": "local_encrypted",
                "local_encrypted": {
                    "master_password": "test_password",
                    "storage_path": "./test_secrets",
                },
            }
        }

        with tempfile.TemporaryDirectory():
            with patch(
                "security.secrets_config_manager.LocalEncryptedSecretsManager"
            ) as mock_manager:
                mock_manager.return_value = Mock()

                config_manager = SecretsConfigManager(mock_config_manager)

                assert config_manager.config_manager == mock_config_manager
                assert config_manager.secrets_config is not None

    def test_api_key_retrieval(self):
        """Test API key retrieval."""
        mock_config_manager = Mock()
        mock_config_manager.load_full_config.return_value = {
            "secrets": {
                "backend": "local_encrypted",
                "local_encrypted": {
                    "master_password": "test_password",
                    "storage_path": "./test_secrets",
                },
            }
        }

        mock_secrets_manager = Mock()
        mock_secrets_manager.get_secret.return_value = "test_api_key"

        config_manager = SecretsConfigManager(mock_config_manager, mock_secrets_manager)

        api_key = config_manager.get_api_key("binance")
        assert api_key == "test_api_key"
        mock_secrets_manager.get_secret.assert_called_with("binance_api_key")

    def test_api_secret_retrieval(self):
        """Test API secret retrieval."""
        mock_config_manager = Mock()
        mock_config_manager.load_full_config.return_value = {
            "secrets": {
                "backend": "local_encrypted",
                "local_encrypted": {
                    "master_password": "test_password",
                    "storage_path": "./test_secrets",
                },
            }
        }

        mock_secrets_manager = Mock()
        mock_secrets_manager.get_secret.return_value = "test_api_secret"

        config_manager = SecretsConfigManager(mock_config_manager, mock_secrets_manager)

        api_secret = config_manager.get_api_secret("binance")
        assert api_secret == "test_api_secret"
        mock_secrets_manager.get_secret.assert_called_with("binance_api_secret")


class TestSecurityManager:
    """Test security manager functionality."""

    def test_security_manager_initialization(self):
        """Test security manager initialization."""
        mock_config_manager = Mock()
        mock_config_manager.load_full_config.return_value = {
            "security": {
                "max_withdrawal_amount_usd": 1000.0,
                "required_ip_whitelist": True,
                "allowed_permission_levels": ["read_only", "trading_only"],
            }
        }

        security_manager = SecurityManager(mock_config_manager)

        assert security_manager.config_manager == mock_config_manager
        assert security_manager.security_config is not None

    @patch("security.security_manager.APIKeyValidator")
    def test_api_key_validation(self, mock_validator_class):
        """Test API key validation."""
        mock_config_manager = Mock()
        mock_config_manager.load_full_config.return_value = {
            "security": {
                "max_withdrawal_amount_usd": 1000.0,
                "required_ip_whitelist": True,
                "allowed_permission_levels": ["read_only", "trading_only"],
            }
        }

        mock_validator = Mock()
        mock_validator.validate_api_key_safety.return_value = APIKeyValidationResult(
            is_safe=True,
            safety_status=SafetyStatus.SAFE,
            permission_level=PermissionLevel.TRADING_ONLY,
            warnings=[],
            errors=[],
            withdrawal_addresses=[],
            ip_whitelist=["192.168.1.1"],
            restrictions={},
        )
        mock_validator_class.return_value = mock_validator

        security_manager = SecurityManager(mock_config_manager)

        result = security_manager.validate_exchange_api_key("binance", "test_key", "test_secret")

        assert result.is_safe is True
        assert result.safety_status == SafetyStatus.SAFE
        mock_validator_class.assert_called_once_with("binance", "test_key", "test_secret")

    def test_trading_safety_check(self):
        """Test trading safety check."""
        mock_config_manager = Mock()
        mock_config_manager.load_full_config.return_value = {
            "security": {
                "max_withdrawal_amount_usd": 1000.0,
                "required_ip_whitelist": True,
                "allowed_permission_levels": ["read_only", "trading_only"],
            }
        }

        security_manager = SecurityManager(mock_config_manager)

        with patch.object(security_manager, "validate_exchange_api_key") as mock_validate:
            mock_validate.return_value = APIKeyValidationResult(
                is_safe=True,
                safety_status=SafetyStatus.SAFE,
                permission_level=PermissionLevel.TRADING_ONLY,
                warnings=[],
                errors=[],
                withdrawal_addresses=[],
                ip_whitelist=["192.168.1.1"],
                restrictions={},
            )

            is_safe = security_manager.is_trading_safe("binance", "test_key", "test_secret")
            assert is_safe is True


class TestIntegration:
    """Integration tests for the complete security system."""

    def test_end_to_end_security_flow(self):
        """Test complete security flow from secrets to validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock config manager
            mock_config_manager = Mock()
            mock_config_manager.load_full_config.return_value = {
                "secrets": {
                    "backend": "local_encrypted",
                    "local_encrypted": {
                        "master_password": "test_password",
                        "storage_path": temp_dir,
                    },
                },
                "security": {
                    "max_withdrawal_amount_usd": 1000.0,
                    "required_ip_whitelist": True,
                    "allowed_permission_levels": ["read_only", "trading_only"],
                },
            }

            # Initialize components
            secrets_config_manager = SecretsConfigManager(mock_config_manager)
            security_manager = SecurityManager(mock_config_manager)

            # Store API credentials
            success = secrets_config_manager.store_api_credentials(
                "binance", "test_api_key", "test_api_secret"
            )
            assert success is True

            # Retrieve API credentials
            api_key = secrets_config_manager.get_api_key("binance")
            api_secret = secrets_config_manager.get_api_secret("binance")

            assert api_key == "test_api_key"
            assert api_secret == "test_api_secret"

            # Validate API key safety (mocked)
            with patch("security.security_manager.APIKeyValidator") as mock_validator_class:
                mock_validator = Mock()
                mock_validator.validate_api_key_safety.return_value = APIKeyValidationResult(
                    is_safe=True,
                    safety_status=SafetyStatus.SAFE,
                    permission_level=PermissionLevel.TRADING_ONLY,
                    warnings=[],
                    errors=[],
                    withdrawal_addresses=[],
                    ip_whitelist=["192.168.1.1"],
                    restrictions={},
                )
                mock_validator_class.return_value = mock_validator

                is_safe = security_manager.is_trading_safe("binance", api_key, api_secret)
                assert is_safe is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
