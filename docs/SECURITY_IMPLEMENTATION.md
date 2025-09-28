# Security Implementation Documentation

## Overview

This document describes the comprehensive security implementation for the Crypto Tracker system, including API key safety controls and enhanced secrets management.

## Architecture

### Security Module Structure

```
src/security/
├── __init__.py                 # Module exports
├── api_key_validator.py        # API key permission validation
├── security_manager.py         # Centralized security orchestration
├── secrets_manager.py          # Abstract secrets management interface
└── secrets_config_manager.py   # Configuration-driven secrets access
```

### Integration Points

- **ExecutionManager**: Uses security validation before creating live executors
- **ConfigManager**: Loads security and secrets configuration
- **Notifier**: Sends security alerts and warnings

## Features Implemented

### 1. API Key Safety Controls

#### APIKeyValidator
- **Permission Validation**: Checks API key permissions (read-only, trading-only, full access, withdrawal-enabled)
- **Withdrawal Detection**: Identifies API keys with withdrawal permissions
- **IP Whitelist Verification**: Ensures API keys are restricted to specific IPs
- **Safety Status Classification**: SAFE/WARNING/UNSAFE/CRITICAL based on configuration
- **Exchange Integration**: Uses CCXT to validate permissions with actual exchanges

#### SecurityManager
- **Centralized Validation**: Orchestrates API key safety checks
- **Caching**: Caches validation results for 24 hours to reduce API calls
- **Alerting**: Integrates with existing notification system
- **Trading Safety**: Determines if trading is safe with given API keys

### 2. Enhanced Secrets Management

#### SecretsManager Interface
- **Abstract Base Class**: Defines interface for all secret storage backends
- **Multiple Backends**: Supports local encrypted, HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager
- **Metadata Tracking**: Tracks creation dates, access patterns, expiration
- **Key Rotation**: Supports manual and automatic key rotation

#### LocalEncryptedSecretsManager
- **AES-256-GCM Encryption**: Military-grade encryption for local storage
- **PBKDF2 Key Derivation**: Secure key derivation from master password
- **Metadata Storage**: JSON-based metadata tracking
- **File-based Storage**: Encrypted files with metadata persistence

#### VaultSecretsManager
- **HashiCorp Vault Integration**: Enterprise-grade secret management
- **KV v2 Engine**: Uses Vault's key-value v2 secret engine
- **Authentication**: Token-based authentication
- **Namespace Support**: Optional Vault namespace support

#### SecretsConfigManager
- **Configuration-driven**: Backend selection through configuration
- **Fallback Support**: Falls back to environment variables if secrets manager unavailable
- **Exchange-specific**: Handles API keys for different exchanges
- **Secure Access**: Provides secure access to API credentials

### 3. Configuration Integration

#### Security Configuration
```yaml
security:
  api_key_safety:
    enabled: true
    max_withdrawal_amount_usd: 1000.0
    required_ip_whitelist: true
    allowed_permission_levels: ["read_only", "trading_only"]
    validation_interval_hours: 24
    
    # Alerting
    alert_on_withdrawal_enabled: true
    alert_on_no_ip_whitelist: true
    alert_on_full_access: true
    
    # Exchange-specific settings
    exchange_settings:
      binance:
        require_subaccount: false
        max_api_keys: 5
      coinbase:
        require_whitelist: true
        max_api_keys: 3
```

#### Secrets Configuration
```yaml
secrets:
  backend: "local_encrypted"  # or "hashicorp_vault", "aws_secrets_manager", "gcp_secret_manager"
  
  local_encrypted:
    master_password_env: "SECRETS_MASTER_PASSWORD"
    storage_path: "./secrets"
    encryption_algorithm: "AES-256-GCM"
  
  vault:
    url: "${VAULT_URL}"
    token: "${VAULT_TOKEN}"
    mount_point: "secret"
    namespace: ""
  
  rotation:
    enabled: true
    interval_days: 30
    auto_rotate: false
    notify_before_days: 7
```

## Usage Examples

### 1. Basic Security Validation

```python
from src.security import SecurityManager
from src.tracker.config_manager import ConfigManager

# Initialize
config_manager = ConfigManager("config/config.yaml")
security_manager = SecurityManager(config_manager)

# Validate API key
result = security_manager.validate_exchange_api_key("binance", "api_key", "secret")

if result.is_safe:
    print(f"✅ API key is safe for trading")
    print(f"Permission level: {result.permission_level.value}")
else:
    print(f"❌ API key is not safe: {result.errors}")
```

### 2. Secrets Management

```python
from src.security import SecretsConfigManager
from src.tracker.config_manager import ConfigManager

# Initialize
config_manager = ConfigManager("config/config.yaml")
secrets_manager = SecretsConfigManager(config_manager)

# Store credentials
secrets_manager.store_api_credentials("binance", "api_key", "secret")

# Retrieve credentials
api_key = secrets_manager.get_api_key("binance")
api_secret = secrets_manager.get_api_secret("binance")
```

### 3. CLI Tool Usage

```bash
# Validate API key safety
python scripts/security_manager.py validate binance --api-key YOUR_KEY --secret YOUR_SECRET

# Store API credentials
python scripts/security_manager.py store binance --api-key YOUR_KEY --secret YOUR_SECRET

# List stored secrets
python scripts/security_manager.py list

# Rotate credentials
python scripts/security_manager.py rotate binance
```

## Security Features

### 1. API Key Safety Controls

- **Permission Validation**: Ensures API keys have appropriate permissions
- **Withdrawal Prevention**: Blocks trading with withdrawal-enabled keys
- **IP Whitelist Enforcement**: Requires IP restrictions
- **Real-time Validation**: Validates keys before trading operations
- **Alerting**: Sends alerts for security violations

### 2. Secrets Management

- **Encrypted Storage**: All secrets encrypted at rest
- **Multiple Backends**: Support for various storage solutions
- **Access Logging**: Audit trail for secret access
- **Key Rotation**: Automated/manual key rotation
- **Fallback Support**: Graceful degradation to environment variables

### 3. Integration Safety

- **Execution Blocking**: Prevents trading with unsafe API keys
- **Configuration Validation**: Validates security configuration
- **Error Handling**: Graceful error handling and fallbacks
- **Logging**: Comprehensive security event logging

## Dependencies

### Required
- `cryptography>=41.0.0`: For encrypted secrets storage

### Optional
- `hvac>=2.0.0`: HashiCorp Vault client
- `boto3>=1.26.0`: AWS Secrets Manager
- `google-cloud-secret-manager>=2.16.0`: GCP Secret Manager

## Testing

Comprehensive test suite covers:
- API key validation logic
- Secrets storage and retrieval
- Security manager orchestration
- Integration testing
- Error handling and edge cases

Run tests with:
```bash
pytest tests/test_security.py -v
```

## Deployment Considerations

### 1. Environment Variables

Set required environment variables:
```bash
export SECRETS_MASTER_PASSWORD="your_secure_password"
export VAULT_URL="https://vault.example.com"  # For Vault backend
export VAULT_TOKEN="your_vault_token"         # For Vault backend
```

### 2. File Permissions

Ensure proper file permissions for secrets storage:
```bash
chmod 700 ./secrets
chmod 600 ./secrets/*.enc
chmod 600 ./secrets/metadata.json
```

### 3. Backup Strategy

- Backup encrypted secrets files
- Store master password securely
- Document key rotation procedures

## Security Best Practices

### 1. API Key Management

- Use trading-only permissions
- Enable IP whitelisting
- Regular key rotation
- Monitor for permission changes

### 2. Secrets Storage

- Use strong master passwords
- Regular key rotation
- Monitor access logs
- Secure backup procedures

### 3. Operational Security

- Regular security audits
- Monitor security alerts
- Test incident response procedures
- Keep dependencies updated

## Troubleshooting

### Common Issues

1. **API Key Validation Fails**
   - Check exchange connectivity
   - Verify API key permissions
   - Review IP whitelist settings

2. **Secrets Manager Initialization Fails**
   - Check configuration syntax
   - Verify environment variables
   - Review file permissions

3. **Security Alerts Not Working**
   - Check notification configuration
   - Verify alert thresholds
   - Review log levels

### Debug Mode

Enable debug logging:
```yaml
ui:
  output:
    log_level: 'debug'
```

## Future Enhancements

### Planned Features

1. **Advanced Vault Integration**
   - Dynamic secret generation
   - Automatic key rotation
   - Policy-based access control

2. **Cloud Provider Integration**
   - AWS Secrets Manager
   - GCP Secret Manager
   - Azure Key Vault

3. **Enhanced Monitoring**
   - Security dashboards
   - Real-time alerts
   - Compliance reporting

4. **Multi-Factor Authentication**
   - TOTP support
   - Hardware key support
   - Biometric authentication

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the test suite for examples
3. Check the configuration documentation
4. Review security logs for details
