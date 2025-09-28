"""
Secrets Configuration Manager

Manages secrets configuration and provides secure access to API keys.
"""

from __future__ import annotations
from typing import Dict, Optional, Any
import logging
import os

from .secrets_manager import SecretsManager, SecretsManagerFactory, SecretBackend, LocalEncryptedSecretsManager

class SecretsConfigManager:
    """Manages secrets configuration and access."""
    
    def __init__(self, config_manager, secrets_manager: Optional[SecretsManager] = None):
        self.config_manager = config_manager
        self.secrets_manager = secrets_manager
        self.logger = logging.getLogger(__name__)
        
        # Load secrets configuration
        self.secrets_config = self._load_secrets_config()
        
        # Initialize secrets manager if not provided
        if not self.secrets_manager:
            self.secrets_manager = self._initialize_secrets_manager()
    
    def get_api_key(self, exchange_name: str) -> Optional[str]:
        """Get API key for exchange."""
        key_name = f"{exchange_name.lower()}_api_key"
        
        # Try secrets manager first
        if self.secrets_manager:
            secret = self.secrets_manager.get_secret(key_name)
            if secret:
                return secret
        
        # Fallback to environment variables
        env_key = os.environ.get(f"{exchange_name.upper()}_API_KEY")
        if env_key:
            self.logger.warning(f"Using environment variable for {exchange_name} API key")
            return env_key
        
        return None
    
    def get_api_secret(self, exchange_name: str) -> Optional[str]:
        """Get API secret for exchange."""
        secret_name = f"{exchange_name.lower()}_api_secret"
        
        # Try secrets manager first
        if self.secrets_manager:
            secret = self.secrets_manager.get_secret(secret_name)
            if secret:
                return secret
        
        # Fallback to environment variables
        env_secret = os.environ.get(f"{exchange_name.upper()}_SECRET")
        if env_secret:
            self.logger.warning(f"Using environment variable for {exchange_name} API secret")
            return env_secret
        
        return None
    
    def store_api_credentials(self, exchange_name: str, api_key: str, api_secret: str) -> bool:
        """Store API credentials securely."""
        if not self.secrets_manager:
            self.logger.error("No secrets manager configured")
            return False
        
        try:
            key_name = f"{exchange_name.lower()}_api_key"
            secret_name = f"{exchange_name.lower()}_api_secret"
            
            success = True
            success &= self.secrets_manager.set_secret(key_name, api_key)
            success &= self.secrets_manager.set_secret(secret_name, api_secret)
            
            if success:
                self.logger.info(f"Stored API credentials for {exchange_name}")
            else:
                self.logger.error(f"Failed to store API credentials for {exchange_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error storing API credentials for {exchange_name}: {e}")
            return False
    
    def _load_secrets_config(self) -> Dict[str, Any]:
        """Load secrets configuration."""
        try:
            config = self.config_manager.load_full_config()
            return config.get('secrets', {
                'backend': 'local_encrypted',
                'local_encrypted': {
                    'master_password': os.environ.get('SECRETS_MASTER_PASSWORD', 'default_password'),
                    'storage_path': './secrets'
                },
                'vault': {
                    'url': os.environ.get('VAULT_URL'),
                    'token': os.environ.get('VAULT_TOKEN'),
                    'mount_point': 'secret'
                }
            })
        except Exception:
            return {}
    
    def _initialize_secrets_manager(self) -> Optional[SecretsManager]:
        """Initialize secrets manager based on configuration."""
        try:
            backend_name = self.secrets_config.get('backend', 'local_encrypted')
            backend = SecretBackend(backend_name)
            
            if backend == SecretBackend.LOCAL_ENCRYPTED:
                config = self.secrets_config.get('local_encrypted', {})
                return SecretsManagerFactory.create_secrets_manager(
                    backend,
                    master_password=config.get('master_password', 'default_password'),
                    storage_path=config.get('storage_path', './secrets')
                )
            
            elif backend == SecretBackend.HASHICORP_VAULT:
                config = self.secrets_config.get('vault', {})
                if not config.get('url') or not config.get('token'):
                    self.logger.error("Vault URL and token required for Vault backend")
                    return None
                
                return SecretsManagerFactory.create_secrets_manager(
                    backend,
                    vault_url=config['url'],
                    vault_token=config['token'],
                    mount_point=config.get('mount_point', 'secret')
                )
            
            else:
                self.logger.error(f"Unsupported secrets backend: {backend_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to initialize secrets manager: {e}")
            return None
