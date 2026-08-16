
# Name: Research Bot
# College: Research
# Roll Number: R-nego_aggressive_accept


# Name: Research Bot
# College: Research
# Roll Number: R-nego-acc
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoAggressiveAccept"

    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = self._value(obs, quote)
        edge_buy = v - ask
        edge_sell = bid - v
        thresh = -0.5
        if "SUBSTITUTE" in obs.powers_mine:
            thresh -= 1.0
        if edge_buy > thresh and edge_buy >= edge_sell:
            return "ACCEPT_BUY"
        if edge_sell > thresh:
            return "ACCEPT_SELL"
        w = max(0, (ask - bid) - self.config.MIN_REDUCTION)
        center = max(bid, min(round(v), ask - w))
        return ("COUNTER", center, center + w)

