
# Name: Research Bot
# College: Research
# Roll Number: R-nego_mid_width


# Name: Research Bot
# College: Research
# Roll Number: R-nego-mid
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoMidWidth"

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        w = (obs.final_cap + obs.spread_cap) // 2
        lo = v - w // 2
        return (lo, lo + w)

