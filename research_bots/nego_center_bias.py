
# Name: Research Bot
# College: Research
# Roll Number: R-nego_center_bias


# Name: Research Bot
# College: Research
# Roll Number: R-nego-bias
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoCenterBias"

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        bias = 1 if obs.is_maker else 0
        cap = obs.final_cap
        lo = (v + bias) - cap // 2
        return (lo, lo + cap)

