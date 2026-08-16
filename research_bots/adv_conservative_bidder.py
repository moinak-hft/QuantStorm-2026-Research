
# Name: Research Bot
# College: Research
# Roll Number: R-adv_conservative_bidder


import random

class Bot:
    name = "ConservativeBidder"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        return {}
    def quote(self, obs):
        v = obs.k_mine
        w = obs.final_cap
        return (v - w // 2, v + (w - w // 2))
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
        return False

