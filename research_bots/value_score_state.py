
# Name: Research Bot
# College: Research
# Roll Number: R-value_score_state


# Name: Research Bot
# College: Research
# Roll Number: R-val-score
from strategies.adaptive_bidder import Bot as BaseBot, POWER_VALUES

class Bot(BaseBot):
    name = "ValueScoreState"

    def _power_value(self, obs, name):
        base = POWER_VALUES.get(name, {}).get(obs.round, 0.5)
        flat = abs(obs.k_mine) <= 1
        if name == "TRANSFORM":
            return base * (1.2 if flat else 0.8)
        if name == "SUBSTITUTE":
            return base * (1.1 if not flat else 0.9)
        return base

