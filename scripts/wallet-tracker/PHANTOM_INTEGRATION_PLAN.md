# 🎯 Phantom Wallet Integration Plan

## 📋 Executive Summary

Based on ChatGPT's analysis, we cannot directly connect Python scripts to Phantom wallet. Phantom requires a frontend component (web/mobile) for signing transactions. This plan outlines a hybrid architecture that combines our Python wallet tracker with a minimal frontend for Phantom integration.

## 🔍 Key Constraints from ChatGPT Analysis

1. **No Direct Python → Phantom Connection**: Phantom's injected provider (`window.phantom.solana`) is only accessible to web pages or mobile apps
2. **Signing Must Happen Client-Side**: Backend cannot request signatures directly from Phantom extension
3. **Architecture Required**: Backend builds transactions → Frontend signs with Phantom → Backend broadcasts

## 🏗️ Proposed Architecture

### **Hybrid System Design**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Python        │    │   Web Frontend   │    │   Phantom       │
│   Wallet        │◄──►│   (Flask/JS)     │◄──►│   Wallet        │
│   Tracker       │    │                  │    │   Extension     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
   Detects Trades          Signs Transactions        User Approval
   Builds Transactions     Returns Signatures       Secure Signing
   Broadcasts Signed TX    Handles Wallet UI        Private Key Safe
```

## 🎯 Implementation Plan

### **Phase 1: Backend Transaction Builder**

#### **1.1 Solana Transaction Construction**
```python
# New file: phantom_integration.py
class PhantomTransactionBuilder:
    def __init__(self, rpc_client, phantom_wallet_address):
        self.rpc_client = rpc_client
        self.phantom_wallet = phantom_wallet_address
    
    def build_swap_transaction(self, trade_data):
        """Build unsigned swap transaction for Phantom signing"""
        # Create swap instruction
        # Set fee payer to Phantom wallet
        # Get recent blockhash
        # Serialize to base64
        return base64_transaction
    
    def broadcast_signed_transaction(self, signed_tx_b64):
        """Broadcast transaction after Phantom signing"""
        # Decode base64
        # Send to Solana network
        # Return transaction signature
```

#### **1.2 Integration with Wallet Tracker**
```python
# Modify wallet_tracker.py
class WalletTracker:
    def __init__(self):
        # Existing initialization...
        self.phantom_enabled = not self.paper_trader.enabled
        if self.phantom_enabled:
            self.phantom_builder = PhantomTransactionBuilder(
                self.rpc_client, 
                self.phantom_wallet_address
            )
    
    async def _execute_real_trade(self, trade_data):
        """Execute real trade via Phantom wallet"""
        if self.phantom_enabled:
            # Build transaction
            unsigned_tx = self.phantom_builder.build_swap_transaction(trade_data)
            
            # Send to frontend for signing
            await self._send_to_frontend(unsigned_tx, trade_data)
        else:
            # Use paper trading
            await self.paper_trader.execute_paper_trade(trade_data)
```

### **Phase 2: Minimal Web Frontend**

#### **2.1 Flask Backend Server**
```python
# New file: phantom_server.py
from flask import Flask, render_template, request, jsonify
import asyncio
import threading

app = Flask(__name__)

class PhantomServer:
    def __init__(self, wallet_tracker):
        self.wallet_tracker = wallet_tracker
        self.pending_transactions = {}
    
    def start_server(self, port=5000):
        """Start Flask server for Phantom integration"""
        app.run(host='0.0.0.0', port=port, debug=False)
    
    @app.route('/')
    def index():
        return render_template('phantom_interface.html')
    
    @app.route('/sign_transaction', methods=['POST'])
    def sign_transaction():
        """Receive transaction from Python tracker"""
        data = request.json
        tx_b64 = data['transaction']
        trade_info = data['trade_info']
        
        # Store pending transaction
        tx_id = str(uuid.uuid4())
        self.pending_transactions[tx_id] = {
            'transaction': tx_b64,
            'trade_info': trade_info,
            'status': 'pending'
        }
        
        return jsonify({
            'tx_id': tx_id,
            'redirect_url': f'/sign/{tx_id}'
        })
```

#### **2.2 Frontend Interface (HTML/JS)**
```html
<!-- templates/phantom_interface.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Phantom Wallet Integration</title>
    <script src="https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js"></script>
</head>
<body>
    <div id="wallet-status">Connecting to Phantom...</div>
    <div id="transaction-info" style="display:none;">
        <h3>New Trade Detected</h3>
        <p id="trade-details"></p>
        <button id="sign-button">Sign Transaction</button>
        <button id="reject-button">Reject</button>
    </div>

    <script>
        // Phantom wallet connection
        const phantom = window.phantom?.solana;
        
        if (phantom && phantom.isPhantom) {
            // Connect to Phantom
            phantom.connect().then(response => {
                document.getElementById('wallet-status').textContent = 
                    `Connected: ${response.publicKey.toString()}`;
            });
            
            // Handle transaction signing
            document.getElementById('sign-button').addEventListener('click', async () => {
                const txData = window.currentTransaction;
                if (txData) {
                    try {
                        const signedTx = await phantom.signTransaction(txData);
                        // Send signed transaction back to Python backend
                        await sendSignedTransaction(signedTx);
                    } catch (error) {
                        console.error('Signing failed:', error);
                    }
                }
            });
        }
    </script>
</body>
</html>
```

### **Phase 3: Configuration Updates**

#### **3.1 Enhanced Configuration**
```yaml
# config/wallet_config.yaml
wallet_tracking:
  paper_trading:
    enabled: false  # Set to false for Phantom mode
    
  phantom_integration:
    enabled: true
    wallet_address: "YOUR_PHANTOM_WALLET_ADDRESS"
    max_position_size_usd: 1000  # Max USD to use from Phantom balance
    buy_percentage_pct: 0.1  # 10% of max position per trade
    frontend_port: 5000
    auto_approve: false  # Require manual approval for each trade
    
  copy_trading:
    enabled: true  # Enable real copy trading
    max_position_size_usd: 1000
    buy_percentage_pct: 0.1
    delay_ms: 2000
```

#### **3.2 Environment Variables**
```bash
# .env file additions
PHANTOM_WALLET_ADDRESS=your_phantom_wallet_address_here
PHANTOM_FRONTEND_PORT=5000
PHANTOM_AUTO_APPROVE=false
```

### **Phase 4: Implementation Steps**

#### **Step 1: Transaction Builder**
1. Install Solana Python SDK: `pip install solana`
2. Create `phantom_integration.py` with transaction building logic
3. Implement swap transaction construction for Jupiter/Raydium
4. Add base64 serialization for frontend communication

#### **Step 2: Flask Server**
1. Install Flask: `pip install flask`
2. Create `phantom_server.py` with Flask routes
3. Implement WebSocket communication for real-time updates
4. Add transaction status tracking

#### **Step 3: Frontend Interface**
1. Create HTML template with Phantom wallet integration
2. Implement JavaScript for wallet connection
3. Add transaction signing UI
4. Handle user approval/rejection flow

#### **Step 4: Integration**
1. Modify `wallet_tracker.py` to use Phantom when paper trading disabled
2. Add configuration loading for Phantom settings
3. Implement real-time communication between Python and frontend
4. Add error handling and fallback mechanisms

## 🔧 Technical Implementation Details

### **Transaction Flow**
1. **Detection**: Python tracker detects wallet trade
2. **Building**: Python builds unsigned swap transaction
3. **Communication**: Python sends transaction to Flask server
4. **Frontend**: Flask serves transaction to web interface
5. **Signing**: User approves transaction in Phantom
6. **Return**: Frontend sends signed transaction back
7. **Broadcast**: Python broadcasts signed transaction
8. **Confirmation**: Python confirms transaction success

### **Security Considerations**
- **No Private Keys**: Phantom keeps private keys secure
- **User Approval**: Each transaction requires explicit user approval
- **Transaction Validation**: Validate all transactions before signing
- **Rate Limiting**: Prevent spam transactions
- **Error Handling**: Graceful fallback to paper trading

### **User Experience**
- **Minimal Interface**: Simple web page for transaction approval
- **Real-time Updates**: Live status of pending transactions
- **Clear Information**: Show trade details before signing
- **Quick Actions**: Approve/reject buttons for fast decisions

## 🎯 Configuration Modes

### **Mode 1: Paper Trading (Default)**
```yaml
paper_trading:
  enabled: true
phantom_integration:
  enabled: false
```
- Uses simulated trading with $1000 balance
- No real money at risk
- Perfect for testing and learning

### **Mode 2: Phantom Integration**
```yaml
paper_trading:
  enabled: false
phantom_integration:
  enabled: true
  wallet_address: "YOUR_PHANTOM_ADDRESS"
  max_position_size_usd: 1000
  buy_percentage_pct: 0.1
```
- Connects to real Phantom wallet
- Uses actual SOL/USDC for trades
- Requires user approval for each transaction

## 🚀 Next Steps

1. **Review this plan** and provide feedback
2. **Choose implementation approach** (Flask server vs other frontend)
3. **Define transaction types** to support (Jupiter swaps, Raydium, etc.)
4. **Set up development environment** with Solana Python SDK
5. **Begin Phase 1 implementation** with transaction builder

## 📊 Benefits

- **Real Trading**: Actual copy trading with real money
- **User Control**: Manual approval for each transaction
- **Security**: Phantom handles private key security
- **Flexibility**: Easy switch between paper and real trading
- **Scalability**: Can add more wallet types later

---

*This plan provides a complete roadmap for integrating Phantom wallet with our existing wallet tracker while maintaining security and user control.*
