
# Name: Research Bot
# College: Research
# Roll Number: R-value_round_te_cond


# Name: Research Bot
# College: Research
# Roll Number: R-val-rte
from strategies.adaptive_bidder import Bot as BaseBot, POWER_VALUES

class Bot(BaseBot):
    name = "ValueRoundTECond"

    def _power_value(self, obs, name):
        base = POWER_VALUES.get(name, {}).get(obs.round, 0.5)
        te_ratio = obs.te_mine / max(1, self.config.TE_BUDGET)
        if name == "FORESIGHT":
            return base * (1.15 if obs.round >= 4 else 1.0)
        if name == "SUBSTITUTE":
            return base * (1.2 if obs.round <= 2 else 0.9)
        if name == "TRICK_ROOM":
            return base * (1.2 if te_ratio > 0.5 else 0.9)
        return base

