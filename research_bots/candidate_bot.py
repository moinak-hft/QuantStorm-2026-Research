# Name: Moinak Goswami
# College: Indian Institute of Technology Ropar
# Roll Number: 2024CSB1225
import random

POWER_VALUES = {
    "FORESIGHT": {1: 0.76, 2: 1.16, 3: 1.48, 4: 1.97, 5: 2.02},
    "TRICK_ROOM": {1: 1.14, 2: 0.0, 3: 0.0, 4: 0.6, 5: 0.52},
    "SUBSTITUTE": {1: 1.46, 2: 1.15, 3: 0.95, 4: 0.57, 5: 0.29},
    "STEALTH_ROCK": {1: 1.51, 2: 0.75, 3: 0.75, 4: 0.75, 5: 0.0},
    "TRANSFORM": {1: 1.58, 2: 1.24, 3: 1.31, 4: 0.0, 5: 0.0},
}

SHADE = 0.65
FLAT_THRESHOLD = 1
OPP_FLAT_THRESHOLD = 2.0
DENIAL_WEIGHT = 0.0


class Bot:
    name = "CandidateBot"

    def reset(self, seat, config, seed):
        self.seat = seat
        self.config = config
        self.rng = random.Random(seed)
        self._anchor = {}
        self._opp_anchor = {}

    def _get_anchor(self, obs, quote):
        r = obs.round
        if r not in self._anchor:
            if (not obs.is_maker) and quote is not None:
                self._anchor[r] = (quote[0] + quote[1]) / 2
                self._opp_anchor[r] = self._anchor[r]
            else:
                self._anchor[r] = 0.0
        return self._anchor[r]

    def _opponent_k(self, obs):
        earlier = [k for k in self._opp_anchor if k < obs.round]
        if not earlier:
            return None
        return self._opp_anchor[max(earlier)]

    def _value(self, obs, quote=None):
        if obs.is_maker or quote is None:
            return float(obs.k_mine + sum(obs.foresight))
        anchor = self._get_anchor(obs, quote)
        if obs.foresight:
            anchor = 0.5 * anchor + 0.5 * sum(obs.foresight)
        return float(anchor + obs.k_mine)

    def _power_value(self, obs, name):
        base = POWER_VALUES.get(name, {}).get(obs.round, 0.5)
        opp_flat = False
        earlier = [k for k in self._opp_anchor if k < obs.round]
        if earlier:
            opp = self._opp_anchor[max(earlier)]
            opp_flat = abs(opp) <= OPP_FLAT_THRESHOLD
        if name == "TRANSFORM" and opp_flat:
            return base * 1.3
        if name == "FORESIGHT" and not opp_flat:
            return base * 1.15
        return base

    def _transform_value(self, obs):
        swap = POWER_VALUES.get("TRANSFORM", {}).get(obs.round, 0.0)
        if abs(obs.k_mine) <= FLAT_THRESHOLD:
            return swap
        opp_k = self._opponent_k(obs)
        if opp_k is not None and abs(opp_k) <= OPP_FLAT_THRESHOLD:
            return swap * DENIAL_WEIGHT
        return 0.0

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        out = {}
        for name in offered:
            if name == "TRANSFORM":
                v = self._transform_value(obs)
            else:
                v = self._power_value(obs, name)
            if v <= 0:
                continue
            fair_te = v / self.config.TE_SALVAGE
            bid_amount = max(0, min(int(fair_te * SHADE), obs.te_mine))
            out[name] = bid_amount
        return out

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        cap = obs.final_cap
        lo = v - cap // 2
        return (lo, lo + cap)

    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = self._value(obs, quote)
        edge_buy = v - ask
        edge_sell = bid - v
        thresh = 0.0
        if "SUBSTITUTE" in obs.powers_mine:
            thresh -= 1.0
        if edge_buy > thresh and edge_buy >= edge_sell:
            return "ACCEPT_BUY"
        if edge_sell > thresh:
            return "ACCEPT_SELL"
        if turn == self.config.N_TURNS:
            if v >= (bid + ask) / 2:
                return "ACCEPT_BUY"
            return "ACCEPT_SELL"
        w = max(0, (ask - bid) - self.config.MIN_REDUCTION)
        center = max(bid, min(round(v), ask - w))
        return ("COUNTER", center, center + w)

    def use_transform(self, obs):
        return abs(obs.k_mine) <= FLAT_THRESHOLD