import numpy as np

class RiskManager:
    def __init__(self, max_position_size=0.08, max_category_exposure=0.20):
        """
        Implements professional risk guardrails.
        :param max_position_size: Max % of total bankroll per single trade (Default 8%)
        :param max_category_exposure: Max % of bankroll in one market type (Default 20%)
        """
        self.max_position_size = max_position_size
        self.max_category_exposure = max_category_exposure

    def calculate_quarter_kelly(self, bankroll, win_probability, price):
        """
        Calculates the Quarter-Kelly fraction using the mathematically correct formula.
        Formula for Kelly in binary markets: f = (p*(b+1) - 1) / b
        where:
          p = win_probability
          b = decimal odds - 1 (which is (1/price) - 1)
        """
        if win_probability <= 0 or price <= 0 or price >= 1:
            return 0.0
        
        # b = decimal odds - 1
        b = (1.0 / price) - 1.0
        
        try:
            # Full Kelly calculation
            kelly_f = (win_probability * (b + 1) - 1) / b
        except ZeroDivisionError:
            return 0.0

        # Apply Quarter-Kelly (Safety Factor to prevent ruin)
        safe_fraction = kelly_f / 4
        
        # Cap at our hard max_position_size
        final_fraction = min(safe_fraction, self.max_position_size)
        
        return max(0.0, final_fraction)

    def validate_trade(self, proposed_size, current_bankroll, category_exposure):
        if proposed_size > (current_bankroll * self.max_position_size):
            return False, "Exceeds max position size"
        
        if category_exposure > self.max_category_exposure:
            return False, "Exceeds category exposure limit"
            
        return True, "Validated"
