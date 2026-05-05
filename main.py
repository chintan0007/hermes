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
        # Note: In a real production environment, we initialize the actual CLOB client here
        self.executor = PolymarketExecutor(client=None, dry_run=self.dry_run)
        self.knowledge_base_path = "knowledge_base.json"
        
        # Telegram Credentials
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        logger.info(f"Bot initialized. Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")

    async def send_telegram_msg(self, message):
        """Helper to send messages to Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials missing. Cannot send message.")
            return

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            params = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.get(url, params=params, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def autopsy_engine(self, trade_details, outcome):
        """
        The Self-Learning Loop.
        """
        logger.info(f"Running Autopsy on trade: {trade_details['id']} | Outcome: {outcome}")
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_details['id'],
            "strategy_params": trade_details['params'],
            "outcome": outcome,
            "reasoning": "Learning from market volatility"
        }

        data = []
        if os.path.exists(self.knowledge_base_path):
            with open(self.knowledge_base_path, "r") as f:
                try:
                    data = json.load(f)
                except:
                    data = []

        data.append(entry)

        with open(self.knowledge_base_path, "w") as f:
            json.dump(data, f, indent=4)
        
        logger.info("Knowledge base updated.")
        
        # Send Autopsy result to Telegram
        await self.send_telegram_msg(f"🧠 **Autopsy Complete**\nTrade ID: `{trade_details['id']}`\nOutcome: `{outcome}`")

    async def run_trading_cycle(self):
        """
        The main loop: Scan -> Predict -> Risk Check -> Execute -> Autopsy
        """
        while True:
            try:
                logger.info("--- Starting New 5-Minute Cycle ---")
                
                # STEP 1: Simulation of ML Prediction
                mock_prediction = {
                    "token_id": "0x12345...",
                    "win_probability": 0.65,
                    "edge": 0.10,
                    "price": 0.60
                }
                
                # STEP 2: Risk Management
                bankroll = 1000.0 
proposed_size_pct = self.risk_manager.calculate_quarter_kelly(
                    bankroll, 
                    mock_prediction['win_probability'], 
                    mock_prediction['edge']
                )
                proposed_amount = bankroll * proposed_size_pct
                
                # STEP 3: Execution
                if proposed_amount > 0:
                    msg = f"🚀 **Trade Signal Detected!**\nSize: `${proposed_amount:.2f}`\nPrice: `{mock_prediction['price']}`"
                    logger.info(msg)
                    
                    # SEND TO TELEGRAM
                    await self.send_telegram_msg(msg)
                    
                    # Execute Order
                    await self.executor.place_limit_order(
                        token_id=mock_prediction['token_id'],
                        side="BUY",
                        size=proposed_amount,
                        price=mock_prediction['price']
                    )
                    
                    # STEP 4: Simulated Autopsy
                    await asyncio.sleep(2) 
                    await self.autopsy_engine(
                        trade_details={"id": "trade_001", "params": mock_prediction},
                        outcome="WIN"
                    )
                else:
                    logger.info("No edge detected. Skipping cycle.")

                logger.info("Cycle complete. Sleeping for 5 minutes...")
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Critical error in main loop: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    # Diagnostic Check on Startup
    print("--- DIAGNOSTIC START ---")
    try:
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        print(f"DEBUG: Token present: {bool(token)}, ChatID present: {bool(chat_id)}")
        if token:
            test_res = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            print(f"Telegram GetMe Result: {test_res.json()}")
        else:
            print("DEBUG: TELEGRAM_TOKEN is MISSING in environment variables!")
    except Exception as e:
        print(f"Diagnostic Error: {e}")
    print("--- DIAGNOSTIC END ---")

    bot = PolymarketAlphaBot()
    try:
        asyncio.run(bot.run_trading_cycle())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
