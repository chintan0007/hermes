import logging
from py_clob_client_v2 import ClobClient 

class PolymarketExecutor:
    def __init__(self, client=None, dry_run=True, api_config=None):
        """
        :param client: An already instantiated ClobClient.
        :param dry_run: If True, no real orders are placed.
        :param api_config: Dict containing 'api_key', 'api_secret', 'private_key', etc.
        """
        self.dry_run = dry_run
        self.logger = logging.getLogger("Executor")
        self.client = client

        if not self.dry_run and self.client is None:
            if api_config:
                self.logger.info("Initializing LIVE ClobClient...")
                self.client = ClobClient(api_config)
            else:
                self.logger.error("CRITICAL: LIVE mode requested but no client or config provided!")
                raise ValueError("Client must be provided for LIVE trading.")

    async def place_limit_order(self, token_id, side, size, price):
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would place {side} order: {size} @ {price} for {token_id}")
            return {"status": "simulated", "order_id": "dry_run_123"}

        try:
            self.logger.info(f"Placing LIVE {side} order: {size} @ {price}")
            order = await self.client.create_order(
                token_id=token_id,
                side=side,
                size=size,
                price=price
            )
            return order
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            raise e

    async def cancel_order(self, order_id):
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would cancel order {order_id}")
            return True
        return await self.client.cancel_order(order_id)
