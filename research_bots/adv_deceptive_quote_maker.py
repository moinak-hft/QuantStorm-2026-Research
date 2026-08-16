
# Name: Research Bot
# College: Research
# Roll Number: R-adv_deceptive_quote_maker


import random

class Bot:
    name = "DeceptiveQuoteMaker"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        return {name: 1 for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        fake = v + (2 if v <= 0 else -2)
        w = obs.final_cap
        return (fake - w // 2, fake + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = obs.k_mine
        if v > ask + 1:
            return "ACCEPT_BUY"
        if v < bid - 1:
            return "ACCEPT_SELL"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = max(bid, min(v, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) <= 1

