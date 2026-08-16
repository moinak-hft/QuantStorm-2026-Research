
# Name: Research Bot
# College: Research
# Roll Number: R-transform_never


import random

class Bot:
    name = "never"

    def reset(self, seat, config, seed):
        self.seat = seat
        self.config = config
        self.rng = random.Random(seed)
        self._anchor = {}

    def _value(self, obs, quote=None):
        if obs.is_maker or quote is None:
            return float(obs.k_mine + sum(obs.foresight))
        if obs.round not in self._anchor:
            if not obs.is_maker and quote is not None:
                self._anchor[obs.round] = (quote[0] + quote[1]) / 2
            else:
                self._anchor[obs.round] = 0.0
        anchor = self._anchor[obs.round]
        if obs.foresight:
            anchor = 0.5 * anchor + 0.5 * sum(obs.foresight)
        return float(anchor + obs.k_mine)

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        out = {}
        for name in offered:
            if name == "TRANSFORM":
                v = 0.0
            else:
                v = 0.0
            if v <= 0:
                continue
            fair_te = v / self.config.TE_SALVAGE
            bid_amount = max(0, min(int(fair_te * 0.6), obs.te_mine))
            out[name] = bid_amount
        return out

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        cap = obs.final_cap
        lo = v - cap // 2
        return (lo, lo + cap)

    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = self._value(obs, quote)
        edge_buy = v - ask
        edge_sell = bid - v
        if edge_buy > 0 and edge_buy >= edge_sell:
            return "ACCEPT_BUY"
        if edge_sell > 0:
            return "ACCEPT_SELL"
        w = max(0, (ask - bid) - self.config.MIN_REDUCTION)
        center = max(bid, min(round(v), ask - w))
        return ("COUNTER", center, center + w)

    def use_transform(self, obs):
        return False

