#!/usr/bin/env python3
"""
Environment Setup Helper

Helps set up environment variables for LLM integration.
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    print("=" * 50)
    
    # Check OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"✅ OPENAI_API_KEY: {openai_key[:20]}...")
    else:
        print("❌ OPENAI_API_KEY: Not set")
    
    # Check Anthropic API key (optional)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print(f"✅ ANTHROPIC_API_KEY: {anthropic_key[:20]}...")
    else:
        print("ℹ️  ANTHROPIC_API_KEY: Not set (optional)")
    
    # Check secrets master password (optional)
    secrets_password = os.getenv("SECRETS_MASTER_PASSWORD")
    if secrets_password:
        print(f"✅ SECRETS_MASTER_PASSWORD: Set")
    else:
        print("ℹ️  SECRETS_MASTER_PASSWORD: Not set (optional)")
    
    print("\n" + "=" * 50)
    
    if not openai_key:
        print("❌ Missing required environment variables!")
        print("\nTo fix this, run:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        print("\nOr add to your shell profile (~/.zshrc or ~/.bashrc):")
        print("echo 'export OPENAI_API_KEY=\"your-api-key-here\"' >> ~/.zshrc")
        return False
    else:
        print("✅ Environment variables are properly configured!")
        return True

def setup_environment():
    """Interactive setup for environment variables"""
    print("🚀 LLM Environment Setup")
    print("=" * 50)
    
    # Get OpenAI API key
    openai_key = input("Enter your OpenAI API key: ").strip()
    if not openai_key:
        print("❌ No API key provided")
        return False
    
    # Get shell profile path
    shell_profile = None
    if os.path.exists(os.path.expanduser("~/.zshrc")):
        shell_profile = "~/.zshrc"
    elif os.path.exists(os.path.expanduser("~/.bashrc")):
        shell_profile = "~/.bashrc"
    else:
        shell_profile = "~/.zshrc"  # Default to zsh
    
    # Add to shell profile
    profile_path = os.path.expanduser(shell_profile)
    export_line = f'export OPENAI_API_KEY="{openai_key}"'
    
    # Check if already exists
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            content = f.read()
            if "OPENAI_API_KEY" in content:
                print(f"✅ OPENAI_API_KEY already exists in {shell_profile}")
            else:
                with open(profile_path, 'a') as f:
                    f.write(f"\n# LLM Integration\n{export_line}\n")
                print(f"✅ Added OPENAI_API_KEY to {shell_profile}")
    else:
        with open(profile_path, 'w') as f:
            f.write(f"# LLM Integration\n{export_line}\n")
        print(f"✅ Created {shell_profile} with OPENAI_API_KEY")
    
    print(f"\nTo apply changes, run:")
    print(f"source {shell_profile}")
    print(f"\nOr restart your terminal")
    
    return True

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_environment()
    else:
        check_environment()

if __name__ == "__main__":
    main()
