# LLM Configuration Options

## Current Configuration (gpt-5-mini - requires credits)
```yaml
llm:
  provider: "openai"
  model: "gpt-5-mini"
```

## Alternative Options (if you have credits for these)

### Option 1: GPT-4o-mini (cheaper)
```yaml
llm:
  provider: "openai"
  model: "gpt-4o-mini"
```

### Option 2: GPT-4o (premium)
```yaml
llm:
  provider: "openai"
  model: "gpt-4o"
```

### Option 3: Claude (Anthropic)
```yaml
llm:
  provider: "anthropic"
  model: "claude-3-haiku-20240307"
```

### Option 4: Disable LLM entirely (current working mode)
```yaml
llm:
  enabled: false
```

## How to Change Configuration

1. **Edit the config file**:
   ```bash
   nano config/config.yaml
   ```

2. **Find the LLM section** (around line 551)

3. **Change the model** to one you have credits for

4. **Or disable LLM** by setting `enabled: false`

## Current Status: ✅ Working Perfectly Without LLM

The script is already working great with **market-based analysis only**:
- ✅ Collects real market data
- ✅ Analyzes market conditions  
- ✅ Generates optimized configurations
- ✅ Provides detailed recommendations
- ✅ No API credits required
