
# Name: Research Bot
# College: Research
# Roll Number: R-nego_wide_quote


# Name: Research Bot
# College: Research
# Roll Number: R-nego-wide
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoWideQuote"

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        cap = obs.spread_cap
        lo = v - cap // 2
        return (lo, lo + cap)

