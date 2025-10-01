# 🤖 LLM Integration Setup Guide

This guide will help you set up LLM integration for enhanced market analysis and crisis detection.

## 🎯 **Recommended LLM Provider: OpenAI GPT-4o Mini**

**Why GPT-4o Mini?**
- ✅ **Cost-effective**: ~$0.15/1M input tokens, ~$0.60/1M output tokens
- ✅ **Fast response times**: Optimized for speed
- ✅ **Reliable API**: Stable and well-documented
- ✅ **Good reasoning**: Sufficient for market analysis tasks
- ✅ **JSON output**: Structured responses for programmatic processing

## 🔑 **Getting Your OpenAI API Key**

### **Step 1: Create OpenAI Account**
1. Go to [https://platform.openai.com](https://platform.openai.com)
2. Sign up for an account
3. Verify your email address

### **Step 2: Add Payment Method**
1. Go to [https://platform.openai.com/account/billing](https://platform.openai.com/account/billing)
2. Add a payment method (credit card)
3. Add at least $5 to your account (minimum for API access)

### **Step 3: Generate API Key**
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Give it a name (e.g., "crypto-tracker")
4. Copy the key immediately (you won't see it again)

### **Step 4: Store API Key Securely**

#### **Option A: Environment Variable (Recommended)**
```bash
# Set the API key as an environment variable
export OPENAI_API_KEY="your-api-key-here"

# To make it permanent, add to your shell profile
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

#### **Option B: Using Secrets Manager (Alternative)**
```bash
# Set your master password for secrets
export SECRETS_MASTER_PASSWORD="your-secure-password"

# Store the API key
python -c "
from src.security.secrets_manager import SecretsManagerFactory
secrets_manager = SecretsManagerFactory.create_secrets_manager('local_encrypted')
secrets_manager.set_secret('openai_api_key', 'your-api-key-here')
print('API key stored securely')
"
```

## ⚙️ **Configuration**

### **Enable LLM Integration**
Edit `config/config.yaml`:
```yaml
llm:
  enabled: true
  provider: "openai"
  model: "gpt-5-mini"  # Latest enhanced model
  # API key loaded from OPENAI_API_KEY environment variable
  # ... other settings
```

### **Alternative Models**
If you want more powerful analysis, you can use:
```yaml
llm:
  model: "gpt-4o"  # More powerful but more expensive
```

## 🧪 **Testing the Integration**

### **Test 1: Basic LLM Connection**
```bash
# Make sure your API key is set
export OPENAI_API_KEY="your-api-key-here"

# Run the test script
python scripts/test_llm_integration.py
```

### **Test 2: Paper Trading with LLM**
```bash
# Run paper trading with LLM integration
python scripts/paper_trading_24_7.py --config config/paper_24_7.yaml
```

## 💰 **Cost Estimation**

### **GPT-4o Mini Costs**
- **Input**: ~$0.15 per 1M tokens
- **Output**: ~$0.60 per 1M tokens
- **Typical analysis**: ~2,000 input tokens, ~500 output tokens
- **Cost per analysis**: ~$0.0006 (less than 1 cent)

### **Daily Usage Estimate**
- **15-minute intervals**: 96 analyses per day
- **Daily cost**: ~$0.06 (6 cents)
- **Monthly cost**: ~$1.80

### **Cost Optimization Tips**
1. **Use caching**: Responses cached for 5 minutes by default
2. **Adjust intervals**: Increase analysis interval to reduce frequency
3. **Use crisis detection**: Only escalate when needed
4. **Monitor usage**: Check OpenAI dashboard regularly

## 🔧 **Troubleshooting**

### **Common Issues**

#### **"No API key configured"**
```bash
# Check if API key is set in environment
echo $OPENAI_API_KEY

# If empty, set it:
export OPENAI_API_KEY="your-api-key-here"
```

#### **"Rate limit exceeded"**
- Reduce `rate_limit_per_minute` in config
- Increase `analysis_interval_minutes`
- Check OpenAI usage dashboard

#### **"Invalid API key"**
- Verify key is correct
- Check account has sufficient credits
- Ensure key has proper permissions

### **Debug Mode**
Enable debug logging:
```yaml
llm:
  enable_caching: false  # Disable caching for debugging
  max_retries: 1  # Reduce retries for faster debugging
```

## 🚀 **Advanced Configuration**

### **Custom Analysis Modes**
```yaml
llm:
  analysis:
    default_mode: "normal"  # normal, alert, crisis, emergency
    crisis_thresholds:
      government_crisis: 0.8
      economic_crisis: 0.7
      regulatory_crisis: 0.8
      market_crisis: 0.9
```

### **Provider Switching**
```yaml
# Switch to Anthropic Claude (more expensive but better reasoning)
llm:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"
```

## 📊 **Monitoring Usage**

### **Check Usage Stats**
```python
# Get LLM usage statistics
from src.llm.client import LLMClient
client = LLMClient(config)
stats = client.get_usage_stats()
print(f"Requests last minute: {stats['requests_last_minute']}")
print(f"Cache size: {stats['cache_size']}")
```

### **OpenAI Dashboard**
Monitor usage at: [https://platform.openai.com/usage](https://platform.openai.com/usage)

## 🎯 **Next Steps**

1. **Set up API key** using the steps above
2. **Test basic connection** with the test script
3. **Run paper trading** with LLM integration
4. **Monitor costs** and adjust settings as needed
5. **Customize analysis** for your specific needs

## 🆘 **Support**

If you encounter issues:
1. Check the troubleshooting section above
2. Review the logs for specific error messages
3. Verify your API key and account status
4. Test with a simple prompt first

---

**Ready to enhance your trading with AI-powered market analysis!** 🚀
