
# Name: Research Bot
# College: Research
# Roll Number: R-xform_round_te_opp


# Name: Research Bot
# College: Research
# Roll Number: R-xf-rto
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "TransformRoundTeOpp"

    def _transform_value(self, obs):
        swap = self._power_value(obs, "TRANSFORM")
        if abs(obs.k_mine) <= 1:
            mult = 1.25 if obs.round == 1 else (1.15 if obs.round == 2 else 1.0)
            if obs.te_mine < obs.te_theirs:
                mult *= 0.9
            return swap * mult
        earlier = [k for k in self._opp_anchor if k < obs.round]
        if earlier:
            opp = self._opp_anchor[max(earlier)]
            if abs(opp) <= 2.0 and obs.te_mine >= obs.te_theirs:
                return swap * 0.6
        return 0.0

    def use_transform(self, obs):
        return abs(obs.k_mine) <= 1 and (obs.round <= 2 or obs.te_mine >= obs.te_theirs)

