
# Name: Research Bot
# College: Research
# Roll Number: R-shade_0_75


# Name: Research Bot
# College: Research
# Roll Number: R-shade_0_75
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "Shade0.75"

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        out = {}
        for name in offered:
            v = self._transform_value(obs) if name == "TRANSFORM" else self._power_value(obs, name)
            if v <= 0:
                continue
            fair_te = v / self.config.TE_SALVAGE
            bid_amount = max(0, min(int(fair_te * 0.75), obs.te_mine))
            out[name] = bid_amount
        return out

