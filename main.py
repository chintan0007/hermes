import asyncio
import logging
import json
import os
import requests
import random
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 1. IMPORT THE SYNTHESIZED COMPONENTS
from engine.risk_manager import RiskManager
from engine.executor import PolymarketExecutor

# 2. THE KRONOS BRIDGE (This connects your ML model to the Bot)
try:
    # This assumes you have moved the Kronos folder into your project root
    from Kronos.model.kronos import KronosModel 
    KRONOS_AVAILABLE = True
    logger.info("✅ KRONOS ML Model successfully linked.")
except ImportError as e:
    KRONOS_AVAILABLE = False
    logger.warning(f"⚠️ KRONOS Model not found. Using simulation mode. Error: {e}")

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
        
        # --- STRATEGY PARAMETERS ---
        self.base_required_edge = 0.05   
        self.current_edge_threshold = 0.05 
        self.base_position_multiplier = 1.0
        self.current_multiplier = 1.0

        # --- PERFORMANCE STATS ---
        self.current_balance = 1000.0
        self.total_pnl = 0.0
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        
        # Initialize Kronos Model if available
        self.ml_engine = KronosModel() if KRONOS_AVAILABLE else None
        
        logger.info(f"INTEGRATED BOT INITIALIZED. Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")

    async def send_telegram_msg(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            params = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}
            requests.get(url, params=params, timeout=10)
        except Exception as e:
            logger.error(f"Telegram Error: {e}")

    async def adjust_strategy_from_memory(self):
        """Self-Learning: Adjusts thresholds based on recent win/loss history."""
        if not os.path.exists(self.knowledge_base_path):
            return

        try:
            with open(self.knowledge_base_path, "r") as f:
                history = [json.loads(line) for line in f if line.strip()]
            
            if len(history) < 3:
                return

            recent_trades = history[-5:]
            recent_wins = sum(1 for t in recent_trades if t['outcome'] == 'WIN')
            recent_loss_rate = (len(recent_trades) - recent_wins) / len(recent_trades)

            if recent_loss_rate > 0.5:
                self.current_edge_threshold = self.base_required_edge + 0.05 
                self.current_multiplier = 0.5 
                logger.warning("⚠️ LOSING STREAK: Tightening constraints.")
            else:
                self.current_edge_threshold = self.base_required_edge
                self.current_multiplier = 1.0
                logger.info("✅ Strategy Stable: Resetting to base parameters.")

        except Exception as e:
            logger.error(f"Learning Error: {e}")

async def autopsy_engine(self, trade_details, outcome):
        """Updates PnL and performs the self-learning update."""
        pnl = trade_details['pnl']
        self.total_pnl += pnl
        self.current_balance += pnl
        self.trades_count += 1
        
        if outcome == "WIN": self.wins += 1
        else: self.losses += 1

        win_rate = (self.wins / self.trades_count) * 100
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_details['id'],
            "outcome": outcome,
            "pnl": pnl,
            "win_rate_at_time": win_rate
        }
        with open(self.knowledge_base_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        report = (
            f"{'✅' if outcome == 'WIN' else '❌'} **TRADE {outcome}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"**Trade #{self.trades_count}** | PnL: `{pnl:+.2f}`\n"
            f"**Win Rate:** `{win_rate:.1f}%` ({self.wins}W/{self.losses}L)\n"
            f"**Total PnL:** `{self.total_pnl:+.2f}`\n"
            f"**Balance:** `${self.current_balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await self.send_telegram_msg(report)

    async def run_trading_cycle(self):
        """The main High-Frequency loop."""
        while True:
            try:
                await self.adjust_strategy_from_memory()

                # --- KRONOS INTEGRATION STEP ---
                # Instead of random numbers, we call the real Kronos model
                if KRONOS_AVAILABLE:
                    logger.info("🤖 Querying KRONOS ML Model for real prediction...")
                    # This calls the actual prediction logic from the Kronos repo
                    prediction = self.ml_engine.predict_next_move() 
                    # Expected format: {'token_id': '...', 'prob': 0.65, 'edge': 0.08, 'price': 0.60}
                else:
                    # Fallback to simulation if Kronos is missing
                    if random.random() > 0.2:
                        await asyncio.sleep(10)
                        continue
                    prediction = {
                        "token_id": "0x123",
                        "win_probability": random.uniform(0.52, 0.70),
                        "edge": random.uniform(0.02, 0.15),
                        "price": 0.60
                    }

                # Apply learned thresholds
                if prediction['edge'] < self.current_edge_threshold:
                    logger.info(f"Signal rejected: Edge {prediction['edge']:.2f} < {self.current_edge_threshold:.2f}")
                    await asyncio.sleep(10)
                    continue

                # Risk Check
                proposed_size_pct = self.risk_manager.calculate_quarter_kelly(
                    self.current_balance, 
                    prediction['win_probability'], 
                    prediction['edge']
                )
                trade_amount = (self.current_balance * proposed_size_pct) * self.current_multiplier
                
                if trade_amount > 5.0:
                    # Telegram: Entry Notification
                    await self.send_telegram_msg(
                        f"🚀 **TRADE OPENED**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"**Token:** `{prediction['token_id']}`\n"
                        f"**Edge:** `{prediction['edge']:.2f}`\n"
                        f"**Size:** `${trade_amount:.2f}`\n"
                        f"**Threshold:** `{self.current_edge_threshold:.2f}`\n"
                        f"━━━━━━━━━━━━━━━━━━"
                    )
                    
                    await self.executor.place_limit_order(
                        prediction['token_id'], "BUY", trade_amount, prediction['price']
                    )
                    
                    # Simulation of resolution
                    await asyncio.sleep(5)
                    outcome = "WIN" if random.random() > 0.4 else "LOSS"
pnl = trade_amount * (0.10 if outcome == "WIN" else -0.08)
                    
                    await self.autopsy_engine({"id": f"T-{random.randint(100,999)}", "pnl": pnl}, outcome)
                
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    # Diagnostic
    print("--- DIAGNOSTIC START ---")
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("TELEGRAM_CHAT_ID")
    if t and c:
        try: print(f"Telegram Test: {requests.get(f'https://api.telegram.org/bot{t}/getMe', timeout=5).json()}")
        except Exception as e: print(f"Error: {e}")
    print("--- DIAGNOSTIC END ---")

    bot = PolymarketAlphaBot()
    asyncio.run(bot.run_trading_cycle())
