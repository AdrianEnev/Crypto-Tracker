#!/usr/bin/env python3
"""
Security Management CLI Tool

Command-line tool for managing API keys, secrets, and security settings.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add src to path before importing modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from security import SecretsConfigManager, SecurityManager  # noqa: E402
from tracker.config_manager import ConfigManager  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Crypto Tracker Security Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate API key command
    validate_parser = subparsers.add_parser("validate", help="Validate API key safety")
    validate_parser.add_argument("exchange", help="Exchange name")
    validate_parser.add_argument("--api-key", help="API key")
    validate_parser.add_argument("--secret", help="API secret")

    # Store credentials command
    store_parser = subparsers.add_parser("store", help="Store API credentials")
    store_parser.add_argument("exchange", help="Exchange name")
    store_parser.add_argument("--api-key", help="API key")
    store_parser.add_argument("--secret", help="API secret")

    # Rotate secrets command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate API credentials")
    rotate_parser.add_argument("exchange", help="Exchange name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize components
    config_manager = ConfigManager("../config/config.yaml")
    secrets_config_manager = SecretsConfigManager(config_manager)
    security_manager = SecurityManager(config_manager)

    if args.command == "validate":
        validate_api_key(args.exchange, args.api_key, args.secret, security_manager)
    elif args.command == "store":
        store_credentials(args.exchange, args.api_key, args.secret, secrets_config_manager)
    elif args.command == "list":
        list_secrets(secrets_config_manager)
    elif args.command == "rotate":
        rotate_credentials(args.exchange, secrets_config_manager)


def validate_api_key(
    exchange: str, api_key: Optional[str], secret: Optional[str], security_manager: SecurityManager
):
    """Validate API key safety."""
    if not api_key or not secret:
        print("Error: API key and secret required for validation")
        return

    result = security_manager.validate_exchange_api_key(exchange, api_key, secret)

    print(f"\n🔐 API Key Validation Results for {exchange.upper()}")
    print("=" * 50)
    print(f"Safety Status: {result.safety_status.value.upper()}")
    print(f"Permission Level: {result.permission_level.value}")
    print(f"Safe for Trading: {'✅ YES' if result.is_safe else '❌ NO'}")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.errors:
        print("\n🚨 Errors:")
        for error in result.errors:
            print(f"  - {error}")

    if result.withdrawal_addresses:
        print("\n💰 Withdrawal Addresses:")
        for addr in result.withdrawal_addresses:
            print(f"  - {addr}")

    if result.ip_whitelist:
        print("\n🌐 IP Whitelist:")
        for ip in result.ip_whitelist:
            print(f"  - {ip}")


def store_credentials(
    exchange: str,
    api_key: Optional[str],
    secret: Optional[str],
    secrets_config_manager: SecretsConfigManager,
):
    """Store API credentials securely."""
    if not api_key or not secret:
        print("Error: API key and secret required for storage")
        return

    success = secrets_config_manager.store_api_credentials(exchange, api_key, secret)
    if success:
        print(f"✅ Successfully stored credentials for {exchange}")
    else:
        print(f"❌ Failed to store credentials for {exchange}")


def list_secrets(secrets_config_manager: SecretsConfigManager):
    """List all stored secrets."""
    if not secrets_config_manager.secrets_manager:
        print("❌ No secrets manager configured")
        return

    secrets = secrets_config_manager.secrets_manager.list_secrets()

    print("\n🔐 Stored Secrets")
    print("=" * 30)

    if not secrets:
        print("No secrets found")
        return

    for key, metadata in secrets.items():
        print(f"Key: {key}")
        print(f"  Backend: {metadata.backend.value}")
        print(f"  Created: {metadata.created_at}")
        print(f"  Last Accessed: {metadata.last_accessed or 'Never'}")
        print()


def rotate_credentials(exchange: str, secrets_config_manager: SecretsConfigManager):
    """Rotate API credentials."""
    if not secrets_config_manager.secrets_manager:
        print("❌ No secrets manager configured")
        return

    success = secrets_config_manager.secrets_manager.rotate_secret(f"{exchange.lower()}_api_key")
    if success:
        print(f"✅ Rotation requested for {exchange} credentials")
    else:
        print(f"❌ Failed to rotate credentials for {exchange}")


if __name__ == "__main__":
    main()
