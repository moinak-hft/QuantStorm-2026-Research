
# Name: Research Bot
# College: Research
# Roll Number: R-adv_wide_quote_maker


import random

class Bot:
    name = "WideQuoteMaker"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        return {name: 1 for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        w = obs.spread_cap
        return (v - w // 2, v + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        if turn == self.config.N_TURNS:
            return "ACCEPT_BUY"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = (bid + ask) // 2
        c = max(bid, min(c, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) <= 1

