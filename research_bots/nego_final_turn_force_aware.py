
# Name: Research Bot
# College: Research
# Roll Number: R-nego_final_turn_force_aware


# Name: Research Bot
# College: Research
# Roll Number: R-nego-force
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoFinalTurnAware"

    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = self._value(obs, quote)
        edge_buy = v - ask
        edge_sell = bid - v
        if edge_buy > 0 and edge_buy >= edge_sell:
            return "ACCEPT_BUY"
        if edge_sell > 0:
            return "ACCEPT_SELL"
        if turn == self.config.N_TURNS:
            if v >= (bid + ask) / 2:
                return "ACCEPT_BUY"
            return "ACCEPT_SELL"
        w = max(0, (ask - bid) - self.config.MIN_REDUCTION)
        center = max(bid, min(round(v), ask - w))
        return ("COUNTER", center, center + w)

