
# Name: Research Bot
# College: Research
# Roll Number: R-te_dynamic_power_slots


# Name: Research Bot
# College: Research
# Roll Number: R-te-dyn
from strategies.adaptive_bidder import Bot as BaseBot, SHADE

class Bot(BaseBot):
    name = "TEDynamicSlots"

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        rounds_left = self.config.N_ROUNDS - obs.round + 1
        reserve = max(0, int(1.2 * rounds_left))
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

