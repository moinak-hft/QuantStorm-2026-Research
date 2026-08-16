
# Name: Research Bot
# College: Research
# Roll Number: R-xform_combined


# Name: Research Bot
# College: Research
# Roll Number: R-xf-comb
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "TransformCombined"

    def _transform_value(self, obs):
        swap = self._power_value(obs, "TRANSFORM")
        if abs(obs.k_mine) <= 1:
            return swap * 1.15
        if obs.round <= 2 and obs.te_mine >= obs.te_theirs:
            return swap * 0.5
        return 0.0

    def use_transform(self, obs):
        if abs(obs.k_mine) <= 1:
            return True
        return False

