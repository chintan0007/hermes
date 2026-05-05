import asyncio
import logging
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

from engine.risk_manager import RiskManager
from engine.executor import PolymarketExecutor

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainBot")

class PolymarketAlphaBot:
    def __init__(self):
        self.dry_run = os.getenv("DRY_RUN", "True").lower() == "true"
        self.risk_manager = RiskManager()
        self.executor = PolymarketExecutor(client=None, dry_run=self.dry_run)
        self.knowledge_base_path = "knowledge_base.json"
        
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # Real-time tracking
        self.current_balance = 1000.0  # In a live bot, this comes from the wallet
        self.total_profit_loss = 0.0
        
        logger.info(f"PRO BOT INITIALIZED. Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")

    async def send_telegram_msg(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            params = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}
            requests.get(url, params=params, timeout=10)
        except Exception as e:
            logger.error(f"Telegram Error: {e}")

    async def autopsy_engine(self, trade_details, outcome):
        """Analyzes trade and calculates PnL."""
        pnl = trade_details['pnl']
        self.total_profit_loss += pnl
        self.current_balance += pnl
        
        status_emoji = "✅" if outcome == "WIN" else "❌"
        
        report = (
            f"{status_emoji} **TRADE COMPLETED**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"**Result:** `{outcome}`\n"
            f"**PnL:** `{pnl:+.2f} USD`\n"
            f"**Total PnL:** `{self.total_profit_loss:+.2f} USD`\n"
            f"**Current Balance:** `${self.current_balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        # Save to Knowledge Base
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_details['id'],
            "outcome": outcome,
            "pnl": pnl
        }
        with open(self.knowledge_base_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        await self.send_telegram_msg(report)

    async def run_trading_cycle(self):
        """The High-Frequency Loop (No long sleeps)"""
        logger.info("Starting High-Frequency Monitoring...")
        
        while True:
            try:
                # 1. SCAN MARKET (Simulated high-frequency check)
                # In production, this would be a WebSocket listener
                mock_prediction = {
                    "token_id": "0x123",
                    "win_probability": 0.65,
                    "edge": 0.10,
"price": 0.60
                }

                # 2. RISK CHECK
                proposed_size_pct = self.risk_manager.calculate_quarter_kelly(
                    self.current_balance, 
                    mock_prediction['win_probability'], 
                    mock_prediction['edge']
                )
                trade_amount = self.current_balance * proposed_size_pct

                # 3. EXECUTE IF SIGNAL IS STRONG
                if trade_amount > 5.0: # Minimum trade threshold
                    logger.info(f"Executing Trade: ${trade_amount:.2f}")
                    
                    # TELEGRAM: Entry Report
                    entry_msg = (
                        f"🚀 **NEW TRADE OPENED**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"**Price:** `{mock_prediction['price']}`\n"
                        f"**Size:** `{trade_amount:.2f} USD`\n"
                        f"**Total Invested:** `${trade_amount:.2f}`\n"
                        f"**Balance Left:** `${self.current_balance - trade_amount:.2f}`\n"
                        f"━━━━━━━━━━━━━━━━━━"
                    )
                    await self.send_telegram_msg(entry_msg)

                    # Execute
                    await self.executor.place_limit_order(
                        "0x123", "BUY", trade_amount, mock_prediction['price']
                    )

                    # 4. SIMULATE OUTCOME (For testing)
                    await asyncio.sleep(5) # Wait for trade to 'resolve'
                    
                    # Mocking a win/loss for the demo
                    outcome = "WIN"
                    pnl = trade_amount * 0.10 # 10% profit
                    
                    await self.autopsy_engine(
                        {"id": "T-101", "pnl": pnl}, 
                        outcome
                    )

                # 5. THE "NO-SLEEP" FIX
                # Instead of 5 minutes, we check every 10 seconds.
                # This ensures we never miss a trade opportunity.
                await asyncio.sleep(10) 

            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    # Diagnostic Check
    print("--- DIAGNOSTIC START ---")
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("TELEGRAM_CHAT_ID")
    if t and c:
        try:
            print(f"Telegram Test: {requests.get(f'https://api.telegram.org/bot{t}/getMe', timeout=5).json()}")
        except Exception as e: print(f"Error: {e}")
    print("--- DIAGNOSTIC END ---")

    bot = PolymarketAlphaBot()
    asyncio.run(bot.run_trading_cycle())
