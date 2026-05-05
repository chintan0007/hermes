import asyncio
import logging
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Import our custom engine components
from engine.risk_manager import RiskManager
from engine.executor import PolymarketExecutor

# Load environment variables
load_dotenv()

# Setup Logging
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
        
        logger.info(f"Bot initialized. Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")

    async def send_telegram_msg(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials missing.")
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            params = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}
            requests.get(url, params=params, timeout=10)
        except Exception as e:
            logger.error(f"Telegram Error: {e}")

    async def autopsy_engine(self, trade_details, outcome):
        logger.info(f"Running Autopsy: {trade_details['id']} | {outcome}")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_details['id'],
            "outcome": outcome
        }
        data = []
        if os.path.exists(self.knowledge_base_path):
            with open(self.knowledge_base_path, "r") as f:
                try: data = json.load(f)
                except: data = []
        data.append(entry)
        with open(self.knowledge_base_path, "w") as f:
            json.dump(data, f, indent=4)
        await self.send_telegram_msg(f"🧠 **Autopsy Complete**\nOutcome: `{outcome}`")

    async def run_trading_cycle(self):
        while True:
            try:
                logger.info("--- Starting Cycle ---")
                mock_prediction = {"token_id": "0x123", "win_probability": 0.65, "edge": 0.10, "price": 0.60}
                bankroll = 1000.0
                proposed_amount = bankroll * self.risk_manager.calculate_quarter_kelly(bankroll, 0.65, 0.10)
                
                if proposed_amount > 0:
                    await self.send_telegram_msg(f"🚀 **Signal!**\nSize: `${proposed_amount:.2f}`")
                    await self.executor.place_limit_order("0x123", "BUY", proposed_amount, 0.60)
                    await asyncio.sleep(2)
                    await self.autopsy_engine({"id": "trade_001"}, "WIN")
                
                logger.info("Cycle complete. Sleeping...")
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    # Diagnostic
    print("--- DIAGNOSTIC START ---")
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("TELEGRAM_CHAT_ID")
    print(f"Token: {bool(t)}, ChatID: {c}")
    if t and c:
        try:
            print(f"Test: {requests.get(f'https://api.telegram.org/bot{t}/getMe', timeout=5).json()}")
        except Exception as e: print(f"Test Error: {e}")
    print("--- DIAGNOSTIC END ---")

    bot = PolymarketAlphaBot()
    asyncio.run(bot.run_trading_cycle())
