
# Name: Research Bot
# College: Research
# Roll Number: R-te_conservative_early


# Name: Research Bot
# College: Research
# Roll Number: R-te-cons
from strategies.adaptive_bidder import Bot as BaseBot, SHADE

class Bot(BaseBot):
    name = "TEConservativeEarly"

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        reserve = 10 if obs.round <= 2 else 4
        budget = max(0, obs.te_mine - reserve)
        out = {}
        for name in offered:
            if budget <= 0:
                break
            v = self._transform_value(obs) if name == "TRANSFORM" else self._power_value(obs, name)
            if v <= 0:
                continue
            fair_te = v / self.config.TE_SALVAGE
            bid = max(0, min(int(fair_te * SHADE), budget))
            if bid > 0:
                out[name] = bid
                budget -= bid
        return out

