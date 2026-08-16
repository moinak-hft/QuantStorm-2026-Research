
# Name: Research Bot
# College: Research
# Roll Number: R-xform_maker_interaction


# Name: Research Bot
# College: Research
# Roll Number: R-xf-maker
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "TransformMakerInteraction"

    def _transform_value(self, obs):
        swap = self._power_value(obs, "TRANSFORM")
        if abs(obs.k_mine) <= 1:
            return swap * (1.2 if obs.is_maker else 1.0)
        return swap * 0.4 if obs.is_maker else 0.0

    def use_transform(self, obs):
        if abs(obs.k_mine) <= 1:
            return True
        return obs.is_maker and obs.round <= 2

