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

    def calculate_quarter_kelly(self, bankroll, win_probability, edge):
        """
        Calculates the Quarter-Kelly fraction to prevent over-leveraging.
        Formula: (bp - q) / b, then divided by 4.
        """
        if edge <= 0:
            return 0.0
        
        # Full Kelly: (Probability * Odds - Probability of loss) / (Odds - 1)
        # Simplified for betting: (edge) / (odds)
        # We use a simplified version for prediction markets:
        kelly_f = edge / (1 - win_probability + 1e-9)
        
        # Apply Quarter-Kelly (Safety First)
        safe_fraction = kelly_f / 4
        
        # Cap it at our hard max_position_size
        final_fraction = min(safe_fraction, self.max_position_size)
        
        return max(0.0, final_fraction)

    def validate_trade(self, proposed_size, current_bankroll, category_exposure):
        """
        Final check before an order is sent.
        """
        if proposed_size > (current_bankroll * self.max_position_size):
            return False, "Exceeds max position size"
        
        if category_exposure > self.max_category_exposure:
            return False, "Exceeds category exposure limit"
            
        return True, "Validated"
