# Meme Coin Discovery Scanner

## Overview

The Meme Coin Discovery Scanner is a sophisticated tool that uses the DexScreener API to identify potential meme coins that might surge in popularity. It applies multiple filters to find tokens with high growth potential while managing risk.

## Features

### 🔍 **Comprehensive Scanning**
- Scans latest tokens from DexScreener
- Monitors trending tokens
- Analyzes 200+ tokens per scan
- Real-time data from multiple DEXs

### 🎯 **Smart Filtering System**
- **Liquidity Filter**: Minimum $15,000 liquidity
- **Volume Filter**: Minimum $100,000 24h volume
- **Market Cap Range**: $700K - $100M (sweet spot for growth)
- **Price Momentum**: Minimum 5% 24h price change
- **Token Age**: Maximum 1 week old (newer = more potential)
- **Meme Patterns**: Detects common meme coin naming patterns
- **DEX Preference**: Prioritizes major DEXs (Uniswap, PancakeSwap, etc.)

### 📊 **Risk Assessment**
- **Risk Score**: 0.0 (low) to 1.0 (high)
- **Potential Score**: 0.0 (low) to 1.0 (high)
- **Filter Pass Rate**: Percentage of filters passed
- **Comprehensive Analysis**: Multiple risk factors considered

### 🚀 **Output Options**
- **Console Report**: Detailed formatted output
- **JSON Export**: Machine-readable results
- **Categorized Results**: Top opportunities, low-risk, high-potential
- **Integration Ready**: Compatible with existing trading system

## Usage

### Basic Usage
```bash
python scripts/meme_coin_discovery.py
```

### Configuration
The scanner uses the `meme_coin_discovery` section in `config/config.yaml`:

```yaml
meme_coin_discovery:
  enabled: true
  meme_coin_filters:
    min_liquidity_usd: 15000
    min_volume_24h_usd: 100000
    min_market_cap_usd: 700000
    max_market_cap_usd: 100000000
    min_price_change_24h_pct: 5.0
    max_age_hours: 168
    meme_patterns:
      - "DOGE"
      - "SHIB"
      - "PEPE"
      # ... more patterns
```

## Filter Criteria

### 1. **Liquidity Requirements**
- Minimum $15,000 liquidity
- Ensures tokens can be traded without major slippage
- Reduces risk of illiquid tokens

### 2. **Volume Requirements**
- Minimum $100,000 24h volume
- Indicates active trading and interest
- Higher volume = more reliable price discovery

### 3. **Market Cap Range**
- Minimum $700,000 market cap
- Maximum $100,000,000 market cap
- Sweet spot for potential growth
- Avoids extremely low-cap (risky) and high-cap (limited upside) tokens

### 4. **Price Momentum**
- Minimum 5% 24h price change
- Indicates positive momentum
- Higher changes may indicate strong interest

### 5. **Token Age**
- Maximum 1 week old
- Newer tokens often have more growth potential
- Reduces risk of established tokens with limited upside

### 6. **Meme Patterns**
- Detects common meme coin naming patterns
- Includes: DOGE, SHIB, PEPE, FLOKI, BONK, WIF, MEME, MOON, etc.
- Helps identify tokens with meme coin characteristics

### 7. **DEX Preference**
- Prioritizes major DEXs
- Includes: Uniswap, PancakeSwap, Raydium, Orca, Jupiter
- More reliable and liquid exchanges

## Risk Assessment

### Risk Score Calculation
- **Low Liquidity Risk**: +0.3 if liquidity < $50K
- **Low Volume Risk**: +0.2 if volume < $500K
- **High Volatility Risk**: +0.3 if price change > 100%
- **High Market Cap Risk**: +0.2 if market cap > $10M

### Potential Score Calculation
- **Filter Pass Rate**: +0.4 if passes ≥70% of filters
- **Strong Momentum**: +0.3 if price change > 20%
- **High Volume**: +0.2 if volume > $1M
- **Meme Pattern**: +0.1 if matches meme patterns

## Output Categories

### 🏆 **Top Opportunities**
- Potential score ≥ 0.4
- Best overall opportunities
- Balanced risk/reward ratio

### 🛡️ **Low-Risk Opportunities**
- Risk score ≤ 0.3
- Potential score > 0.3
- Safer investments with decent potential

### 🚀 **High-Potential Opportunities**
- Potential score ≥ 0.6
- Highest growth potential
- May have higher risk

## Integration with Trading System

### Configuration Integration
- Uses existing `ConfigManager`
- Follows project's configuration patterns
- Compatible with secrets management

### Data Export
- JSON format for further processing
- Timestamped results
- Includes all filter results and scores

### Future Enhancements
- Integration with trading watchlist
- Automated alerts for high-potential finds
- Social media sentiment analysis
- On-chain data integration

## Example Output

```
🚀 MEME COIN DISCOVERY SCANNER REPORT
================================================================================
📅 Scan Time: 2024-01-15 14:30:25
🔍 Total Tokens Analyzed: 45
✅ Potential Meme Coins Found: 12

🏆 TOP MEME COIN OPPORTUNITIES (Potential Score ≥ 0.4)
--------------------------------------------------------------------------------
Rank Symbol       Name                     Price        24h Vol      24h Chg    Liquidity    Potential  Risk    
--------------------------------------------------------------------------------
1    PEPE2.0      Pepe 2.0                $0.00000123  $2,450,000   +45.2%     $89,000      0.85       0.25    
2    DOGEAI       Doge AI                  $0.00004567  $1,890,000   +32.1%     $156,000     0.78       0.30    
3    MOONCAT      Moon Cat                 $0.00001234  $1,234,000   +28.7%     $78,000      0.72       0.35    
```

## Dependencies

### Required Packages
- `aiohttp`: Async HTTP client for API calls
- `yaml`: Configuration file parsing
- `asyncio`: Async programming support

### Project Dependencies
- Uses existing `ConfigManager`
- Integrates with `SecretsConfigManager`
- Follows project's logging patterns

## Rate Limiting

### API Limits
- 1 second between requests
- Respects DexScreener rate limits
- Graceful error handling

### Performance
- Async processing for speed
- Concurrent token analysis
- Efficient data processing

## Security Considerations

### API Usage
- No API keys required for DexScreener
- Public API endpoints only
- Rate limiting to prevent abuse

### Data Validation
- Input validation for all API responses
- Error handling for malformed data
- Safe defaults for missing data

## Troubleshooting

### Common Issues

1. **No results found**
   - Check internet connectivity
   - Verify DexScreener API status
   - Adjust filter criteria

2. **API errors**
   - Check rate limiting
   - Verify API endpoint availability
   - Check for network issues

3. **Configuration errors**
   - Verify `config.yaml` format
   - Check `meme_coin_discovery` section
   - Validate filter values

### Debug Mode
Enable debug logging by modifying the script:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features
- **Social Media Integration**: Twitter/Reddit sentiment analysis
- **On-Chain Analysis**: Whale movements, holder distribution
- **Automated Alerts**: Telegram/Discord notifications
- **Portfolio Integration**: Direct watchlist addition
- **Backtesting**: Historical performance analysis

### Advanced Filters
- **Holder Distribution**: Analyze token holder patterns
- **Contract Analysis**: Smart contract risk assessment
- **Liquidity Analysis**: Depth and stability metrics
- **Volume Patterns**: Unusual volume spike detection

## Disclaimer

⚠️ **IMPORTANT DISCLAIMERS**

- This tool is for **research purposes only**
- **Not financial advice** - always do your own research
- Meme coins are **highly volatile and risky**
- **Only invest what you can afford to lose**
- Past performance does not guarantee future results
- Always verify token legitimacy before investing

## Contributing

### Development
- Follow existing code patterns
- Add comprehensive error handling
- Include unit tests for new features
- Update documentation

### Testing
- Test with various filter configurations
- Verify API integration
- Check error handling scenarios
- Validate output formats

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review configuration settings
3. Check project documentation
4. Create an issue in the project repository

---

**Happy meme coin hunting! 🚀🐕**
