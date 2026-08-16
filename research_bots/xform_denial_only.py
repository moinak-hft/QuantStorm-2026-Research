
# Name: Research Bot
# College: Research
# Roll Number: R-xform_denial_only


# Name: Research Bot
# College: Research
# Roll Number: R-xf-deny
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "TransformDenialOnly"

    def _transform_value(self, obs):
        swap = self._power_value(obs, "TRANSFORM")
        return swap * 0.8 if abs(obs.k_mine) > 1 else 0.0

    def use_transform(self, obs):
        return False

