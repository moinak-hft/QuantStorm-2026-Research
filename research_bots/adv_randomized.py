
# Name: Research Bot
# College: Research
# Roll Number: R-adv_randomized


import random

class Bot:
    name = "Randomized"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        out = {}
        rem = obs.te_mine
        for name in offered:
            b = self.rng.randint(0, rem) if rem > 0 else 0
            out[name] = b
            rem -= b
        return out
    def quote(self, obs):
        v = obs.k_mine + self.rng.choice([-1, 0, 1])
        w = self.rng.randint(obs.final_cap, obs.spread_cap)
        lo = v - w // 2
        return (lo, lo + w)
    def respond(self, obs, quote, turn):
        bid, ask = quote
        if self.rng.random() < 0.25:
            return "ACCEPT_BUY"
        if self.rng.random() < 0.25:
            return "ACCEPT_SELL"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = self.rng.randint(bid, ask) if bid <= ask else bid
        c = max(bid, min(c, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return self.rng.random() < 0.5

