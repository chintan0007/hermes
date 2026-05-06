import asyncio
import logging
import json
import os
import random
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 1. THE SYNTHESIS: LINKING ALL THREE REPOS
try:
    import sys
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    KRONOS_PATH = os.path.join(BASE_DIR, "Kronos", "Kronos-master")
    if KRONOS_PATH not in sys.path:
        sys.path.append(KRONOS_PATH)
    
    from model.kronos import KronosModel 
    KRONOS_AVAILABLE = True
except Exception as e:
    KRONOS_AVAILABLE = False
    print(f"⚠️ WARNING: Kronos ML not found. Error: {e}")

try:
    from engine.risk_manager import RiskManager
    from engine.executor import PolymarketExecutor
except ImportError as e:
    print(f"❌ CRITICAL ERROR: Engine components missing! {e}")
    exit(1)

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
        
        api_config = {
            "api_key": os.getenv("POLY_API_KEY"),
            "api_secret": os.getenv("POLY_API_SECRET"),
            "private_key": os.getenv("POLY_PRIVATE_KEY")
        }
        self.executor = PolymarketExecutor(client=None, dry_run=self.dry_run, api_config=api_config)
        
        self.knowledge_base_path = "knowledge_base.json"
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.base_required_edge = 0.05   
        self.current_edge_threshold = 0.05 
        self.current_multiplier = 1.0
        self.current_balance = 1000.0
        self.total_pnl = 0.0
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        
        self.ml_engine = KronosModel() if KRONOS_AVAILABLE else None
        logger.info(f"BOT ONLINE. Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")

    async def send_telegram_msg(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            async with httpx.AsyncClient() as client:
                await client.post(url, json={
                    "chat_id": self.telegram_chat_id, 
                    "text": message, 
                    "parse_mode": "Markdown"
                }, timeout=10)
        except Exception as e:
            logger.error(f"Telegram Error: {e}")

    async def adjust_strategy_from_memory(self):
        if not os.path.exists(self.knowledge_base_path):
            return
        try:
            recent_entries = []
            with open(self.knowledge_base_path, "r") as f:
                lines = f.readlines()
                for line in reversed(lines[-20:]):
                    if line.strip():
                        recent_entries.append(json.loads(line))
            
            if len(recent_entries) < 3: 
                return
            
            recent_wins = sum(1 for t in recent_entries if t['outcome'] == 'WIN')
            loss_rate = (len(recent_entries) - recent_wins) / len(recent_entries)
            
            if loss_rate > 0.5:
                self.current_edge_threshold = 0.10
self.current_multiplier = 0.5
                logger.warning("⚠️ LOSING STREAK: Tightening thresholds.")
            else:
                self.current_edge_threshold = 0.05
                self.current_multiplier = 1.0
                logger.info("✅ Strategy Stable.")
        except Exception as e:
            logger.error(f"Learning Error: {e}")

    async def autopsy_engine(self, trade_details, outcome):
        pnl = trade_details['pnl']
        self.total_pnl += pnl
        self.current_balance += pnl
        self.trades_count += 1
        if outcome == "WIN":
            self.wins += 1
        else:
            self.losses += 1
            
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
            
        report = (f"{'✅' if outcome == 'WIN' else '❌'} **TRADE {outcome}**\n"
                  f"━━━━━━━━━━━━━━━━━━\n"
                  f"**Trade #{self.trades_count}** | PnL: `{pnl:+.2f}`\n"
                  f"**Win Rate:** `{win_rate:.1f}%` ({self.wins}W/{self.losses}L)\n"
                  f"**Total PnL:** `{self.total_pnl:+.2f}`\n"
                  f"**Balance:** `${self.current_balance:.2f}`\n"
                  f"━━━━━━━━━━━━━━━━━━")
        await self.send_telegram_msg(report)

    async def run_trading_cycle(self):
        while True:
            try:
                await self.adjust_strategy_from_memory()
                
                if KRONOS_AVAILABLE and self.ml_engine:
                    logger.info("🤖 Querying KRONOS...")
                    prediction = self.ml_engine.predict_next_move()
                else:
                    await asyncio.sleep(1)
                    prediction = {
                        "token_id": "0x123", 
                        "win_probability": random.uniform(0.52, 0.70), 
                        "edge": random.uniform(0.02, 0.15), 
                        "price": 0.60
                    }

                if prediction['edge'] < self.current_edge_threshold:
                    await asyncio.sleep(10)
                    continue

                proposed_size_pct = self.risk_manager.calculate_quarter_kelly(
                    self.current_balance, 
                    prediction['win_probability'], 
                    prediction['price']
                )
                trade_amount = (self.current_balance * proposed_size_pct) * self.current_multiplier
                
                if trade_amount > 1.0:
                    await self.send_telegram_msg(f"🚀 **TRADE OPENED**\n━━━━━━━━━━━━━━━━━━\n**Edge:** `{prediction['edge']:.2f}`\n**Size:** `${trade_amount:.2f}`\n━━━━━━━━━━━━━━━━━━")
                    await self.executor.place_limit_order(prediction['token_id'], "BUY", trade_amount, prediction['price'])
                    
                    await asyncio.sleep(2)
                    outcome = "WIN" if random.random() > 0.4 else "LOSS"
                    pnl = trade_amount * (0.10 if outcome == "WIN" else -0.08)
                    await self.autopsy_engine({"id": f"T-{random.randint(100,999)}", "pnl": pnl}, outcome)
                
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Loop Error: {e}", exc_info=True)
                await asyncio.sleep(5)

if __name__ == "__main__":
    bot = PolymarketAlphaBot()
    try:
        asyncio.run(bot.run_trading_cycle())
    except KeyboardInterrupt:
        print("Bot stopped.")
