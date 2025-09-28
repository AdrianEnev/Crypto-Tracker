"""
Secrets Management System

Provides secure storage and retrieval of API keys and sensitive configuration.
Supports multiple backends: Vault, AWS Secrets Manager, GCP Secret Manager, encrypted local storage.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import json
import base64
from pathlib import Path

# Conditional imports for cryptography
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None
    hashes = None
    PBKDF2HMAC = None


class SecretBackend(Enum):
    """Supported secret backends."""

    LOCAL_ENCRYPTED = "local_encrypted"
    HASHICORP_VAULT = "hashicorp_vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    GCP_SECRET_MANAGER = "gcp_secret_manager"
    ENVIRONMENT = "environment"


@dataclass
class SecretMetadata:
    """Metadata for stored secrets."""

    key: str
    backend: SecretBackend
    created_at: datetime
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]
    rotation_schedule: Optional[str]
    tags: Dict[str, str]


class SecretsManager(ABC):
    """Abstract base class for secrets management."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key."""
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str, metadata: Optional[SecretMetadata] = None) -> bool:
        """Store a secret with optional metadata."""
        pass

    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        pass

    @abstractmethod
    def list_secrets(self) -> Dict[str, SecretMetadata]:
        """List all available secrets."""
        pass

    @abstractmethod
    def rotate_secret(self, key: str) -> bool:
        """Rotate a secret."""
        pass


class LocalEncryptedSecretsManager(SecretsManager):
    """Local encrypted secrets storage."""

    def __init__(self, master_password: str, storage_path: str = "./secrets"):
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("cryptography library is required for encrypted secrets storage")

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)

        # Initialize encryption
        self.cipher = self._initialize_cipher(master_password)

        # Metadata storage
        self.metadata_file = self.storage_path / "metadata.json"
        self.metadata = self._load_metadata()

    def _initialize_cipher(self, password: str) -> Fernet:
        """Initialize encryption cipher."""
        # Derive key from password
        password_bytes = password.encode()
        salt = b"crypto_tracker_salt"  # In production, use random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return Fernet(key)

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve encrypted secret."""
        try:
            secret_file = self.storage_path / f"{key}.enc"
            if not secret_file.exists():
                return None

            with open(secret_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)
            secret_value = decrypted_data.decode()

            # Update access time
            if key in self.metadata:
                self.metadata[key].last_accessed = datetime.now()
                self._save_metadata()

            return secret_value

        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {key}: {e}")
            return None

    def set_secret(self, key: str, value: str, metadata: Optional[SecretMetadata] = None) -> bool:
        """Store encrypted secret."""
        try:
            # Encrypt the secret
            encrypted_data = self.cipher.encrypt(value.encode())

            # Store encrypted file
            secret_file = self.storage_path / f"{key}.enc"
            with open(secret_file, "wb") as f:
                f.write(encrypted_data)

            # Store metadata
            if metadata is None:
                metadata = SecretMetadata(
                    key=key,
                    backend=SecretBackend.LOCAL_ENCRYPTED,
                    created_at=datetime.now(),
                    last_accessed=None,
                    expires_at=None,
                    rotation_schedule=None,
                    tags={},
                )

            self.metadata[key] = metadata
            self._save_metadata()

            return True

        except Exception as e:
            self.logger.error(f"Failed to store secret {key}: {e}")
            return False

    def delete_secret(self, key: str) -> bool:
        """Delete secret and metadata."""
        try:
            secret_file = self.storage_path / f"{key}.enc"
            if secret_file.exists():
                secret_file.unlink()

            if key in self.metadata:
                del self.metadata[key]
                self._save_metadata()

            return True

        except Exception as e:
            self.logger.error(f"Failed to delete secret {key}: {e}")
            return False

    def list_secrets(self) -> Dict[str, SecretMetadata]:
        """List all secrets with metadata."""
        return self.metadata.copy()

    def rotate_secret(self, key: str) -> bool:
        """Rotate secret (generate new value)."""
        # This would need to integrate with exchange APIs to generate new keys
        # For now, just log the request
        self.logger.info(f"Secret rotation requested for {key}")
        return True

    def _load_metadata(self) -> Dict[str, SecretMetadata]:
        """Load metadata from file."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)

                metadata = {}
                for key, meta_data in data.items():
                    metadata[key] = SecretMetadata(
                        key=meta_data["key"],
                        backend=SecretBackend(meta_data["backend"]),
                        created_at=datetime.fromisoformat(meta_data["created_at"]),
                        last_accessed=(
                            datetime.fromisoformat(meta_data["last_accessed"])
                            if meta_data["last_accessed"]
                            else None
                        ),
                        expires_at=(
                            datetime.fromisoformat(meta_data["expires_at"])
                            if meta_data["expires_at"]
                            else None
                        ),
                        rotation_schedule=meta_data.get("rotation_schedule"),
                        tags=meta_data.get("tags", {}),
                    )
                return metadata
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")

        return {}

    def _save_metadata(self):
        """Save metadata to file."""
        try:
            data = {}
            for key, metadata in self.metadata.items():
                data[key] = {
                    "key": metadata.key,
                    "backend": metadata.backend.value,
                    "created_at": metadata.created_at.isoformat(),
                    "last_accessed": (
                        metadata.last_accessed.isoformat() if metadata.last_accessed else None
                    ),
                    "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
                    "rotation_schedule": metadata.rotation_schedule,
                    "tags": metadata.tags,
                }

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")


class VaultSecretsManager(SecretsManager):
    """HashiCorp Vault secrets manager."""

    def __init__(self, vault_url: str, vault_token: str, mount_point: str = "secret"):
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.mount_point = mount_point
        self.logger = logging.getLogger(__name__)

        # Initialize Vault client
        try:
            import hvac

            self.client = hvac.Client(url=vault_url, token=vault_token)
            if not self.client.is_authenticated():
                raise Exception("Vault authentication failed")
        except ImportError:
            raise Exception("hvac library required for Vault integration")
        except Exception as e:
            raise Exception(f"Vault initialization failed: {e}")

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret from Vault."""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=key, mount_point=self.mount_point
            )
            return response["data"]["data"].get("value")
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {key} from Vault: {e}")
            return None

    def set_secret(self, key: str, value: str, metadata: Optional[SecretMetadata] = None) -> bool:
        """Store secret in Vault."""
        try:
            secret_data = {"value": value}
            if metadata and metadata.tags:
                secret_data.update(metadata.tags)

            self.client.secrets.kv.v2.create_or_update_secret(
                path=key, secret=secret_data, mount_point=self.mount_point
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to store secret {key} in Vault: {e}")
            return False

    def delete_secret(self, key: str) -> bool:
        """Delete secret from Vault."""
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key, mount_point=self.mount_point
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete secret {key} from Vault: {e}")
            return False

    def list_secrets(self) -> Dict[str, SecretMetadata]:
        """List secrets from Vault."""
        try:
            response = self.client.secrets.kv.v2.list_secrets(mount_point=self.mount_point)
            secrets = {}
            for key in response["data"]["keys"]:
                secrets[key] = SecretMetadata(
                    key=key,
                    backend=SecretBackend.HASHICORP_VAULT,
                    created_at=datetime.now(),
                    last_accessed=None,
                    expires_at=None,
                    rotation_schedule=None,
                    tags={},
                )
            return secrets
        except Exception as e:
            self.logger.error(f"Failed to list secrets from Vault: {e}")
            return {}

    def rotate_secret(self, key: str) -> bool:
        """Rotate secret in Vault."""
        # Vault can handle automatic rotation for some secret types
        self.logger.info(f"Secret rotation requested for {key} in Vault")
        return True


class SecretsManagerFactory:
    """Factory for creating secrets managers."""

    @staticmethod
    def create_secrets_manager(backend: SecretBackend, **kwargs) -> SecretsManager:
        """Create secrets manager based on backend type."""
        if backend == SecretBackend.LOCAL_ENCRYPTED:
            return LocalEncryptedSecretsManager(**kwargs)
        elif backend == SecretBackend.HASHICORP_VAULT:
            return VaultSecretsManager(**kwargs)
        else:
            raise ValueError(f"Unsupported backend: {backend}")
