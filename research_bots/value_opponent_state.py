
# Name: Research Bot
# College: Research
# Roll Number: R-value_opponent_state


# Name: Research Bot
# College: Research
# Roll Number: R-val-opp
from strategies.adaptive_bidder import Bot as BaseBot, POWER_VALUES

class Bot(BaseBot):
    name = "ValueOpponentState"

    def _power_value(self, obs, name):
        base = POWER_VALUES.get(name, {}).get(obs.round, 0.5)
        opp_flat = False
        earlier = [k for k in self._opp_anchor if k < obs.round]
        if earlier:
            opp = self._opp_anchor[max(earlier)]
            opp_flat = abs(opp) <= 2.0
        if name == "TRANSFORM" and opp_flat:
            return base * 1.3
        if name == "FORESIGHT" and not opp_flat:
            return base * 1.15
        return base

