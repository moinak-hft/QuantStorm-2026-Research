
# Name: Research Bot
# College: Research
# Roll Number: R-adv_aggressive_bidder


import random

class Bot:
    name = "AggressiveBidder"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        if not offered:
            return {}
        return {name: max(0, min(obs.te_mine // max(1, len(offered)), obs.te_mine)) for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        w = obs.final_cap
        return (v - w // 2, v + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = obs.k_mine
        if v > ask:
            return "ACCEPT_BUY"
        if v < bid:
            return "ACCEPT_SELL"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = max(bid, min(v, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) <= 2

