import asyncio
import logging
import json
import os
import requests
import random  # Added for realistic signal simulation
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
        
        # --- PRO TRACKING STATS ---
        self.current_balance = 1000.0
        self.total_pnl = 0.0
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        
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
        """Processes the result and updates performance stats."""
        pnl = trade_details['pnl']
        self.total_pnl += pnl
        self.current_balance += pnl
        self.trades_count += 1
        
        if outcome == "WIN":
            self.wins += 1
        else:
            self.losses += 1

        win_rate = (self.wins / self.trades_count) * 100

        # --- BEAUTIFUL PROFESSIONAL REPORT ---
        report = (
            f"{'✅' if outcome == 'WIN' else '❌'} **TRADE {outcome}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"**Trade #{self.trades_count}**\n"
            f"**PnL:** `{pnl:+.2f} USD`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 **PERFORMANCE STATS**\n"
            f"**Total Trades:** `{self.trades_count}`\n"
            f"**Win Rate:** `{win_rate:.1f}%` ({self.wins}W / {self.losses}L)\n"
            f"**Total PnL:** `{self.total_pnl:+.2f} USD`\n"
            f"**Balance:** `${self.current_balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        # Save to knowledge base
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_details['id'],
            "outcome": outcome,
            "pnl": pnl,
            "win_rate": win_rate
        }
        with open(self.knowledge_base_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        await self.send_telegram_msg(report)

    async def run_trading_cycle(self):
        logger.info("Starting High-Frequency Monitoring...")
        
        while True:
            try:
                # --- THE STRATEGY FIX: RANDOMIZED SIGNAL ---
                # We simulate a real market where signals are rare.
                # A '0.1' means there is a 10% chance of a trade signal every loop.
                if random.random() > 0.15: 
                    # No signal this time, just sleep and check again
                    await asyncio.sleep(10)
                    continue

                logger.info("🔥 SIGNAL DETECTED! Analyzing edge...")

                # Simulate ML prediction
                mock_prediction = {
                    "token_id": "0x123",
                    "win_probability": random.uniform(0.55, 0.75), # Random edge
                    "edge": random.uniform(0.05, 0.15),
                    "price": 0.60
                }
# Risk Check
                proposed_size_pct = self.risk_manager.calculate_quarter_kelly(
                    self.current_balance, 
                    mock_prediction['win_probability'], 
                    mock_prediction['edge']
                )
                trade_amount = self.current_balance * proposed_size_pct
                
                if trade_amount > 5.0:
                    # 1. Notify Entry
                    entry_msg = (
                        f"🚀 **NEW TRADE OPENED**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"**Price:** `{mock_prediction['price']}`\n"
                        f"**Size:** `{trade_amount:.2f} USD`\n"
                        f"**Balance Left:** `${self.current_balance - trade_amount:.2f}`\n"
                        f"━━━━━━━━━━━━━━━━━━"
                    )
                    await self.send_telegram_msg(entry_msg)
                    
                    # 2. Execute
                    await self.executor.place_limit_order(
                        "0x123", "BUY", trade_amount, mock_prediction['price']
                    )
                    
                    # 3. Wait for market resolution (Simulated)
                    await asyncio.sleep(5) 
                    
                    # 4. Simulate Outcome (Random Win/Loss)
                    outcome = "WIN" if random.random() > 0.4 else "LOSS" # 60% win rate sim
                    pnl = trade_amount * (0.10 if outcome == "WIN" else -0.08)
                    
                    await self.autopsy_engine(
                        {"id": f"T-{self.trades_count+100}", "pnl": pnl}, 
                        outcome
                    )
                
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    # Diagnostic Check
    print("--- DIAGNOSTIC START ---")
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            print(f"Telegram Test: {requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=5).json()}")
        except Exception as e: print(f"Error: {e}")
    print("--- DIAGNOSTIC END ---")

    bot = PolymarketAlphaBot()
    asyncio.run(bot.run_trading_cycle())
