from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import textwrap
from pathlib import Path
from typing import Iterable

from engine import play_match
from game_config import GameConfig, Obs
from bot_loader import load_for_testing as load_bot_class

WORKSPACE = Path(__file__).resolve().parent
RESEARCH_DIR = WORKSPACE / "research_bots"
RESEARCH_DIR.mkdir(exist_ok=True)
RESULTS_DIR = WORKSPACE / "research_results"
RESULTS_DIR.mkdir(exist_ok=True)


def mean(xs):
    return statistics.mean(xs) if xs else 0.0


def stddev(xs):
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def stderror(xs):
    return stddev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0


def load_bot_for_research(path: str):
    p = Path(path)
    module_name = f"_research_bot_{p.stem}_{abs(hash(str(p.resolve())))}"
    spec = importlib.util.spec_from_file_location(module_name, str(p))
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "Bot"):
        raise AttributeError(f"{path} has no Bot class")
    return module.Bot


def summarize_pair(path_a: str, path_b: str, seeds: Iterable[int], n_deals: int = 10, mirror: bool = True):
    seed_list = list(seeds)
    scores = []
    direct_scores = []
    mirror_scores = []
    wins = 0
    losses = 0
    draws = 0
    for seed in seed_list:
        BotA = load_bot_for_research(path_a)
        BotB = load_bot_for_research(path_b)
        result = play_match(
            BotA,
            BotB,
            config=GameConfig(),
            seed=seed,
            mirror=mirror,
            n_deals=n_deals,
            verbose=False,
            bot_a_name=Path(path_a).stem,
            bot_b_name=Path(path_b).stem,
        )
        scores.append(result.pnl[0])
        if result.pnl[0] > 0:
            wins += 1
        elif result.pnl[0] < 0:
            losses += 1
        else:
            draws += 1
        direct_total = 0.0
        mirror_total = 0.0
        for idx, d in enumerate(result.deals):
            if idx % 2 == 0:
                direct_total += d.pnl[0]
            else:
                mirror_total += d.pnl[0]
        direct_scores.append(direct_total)
        mirror_scores.append(mirror_total)
    return {
        "bot_a": path_a,
        "bot_b": path_b,
        "n_seeds": len(seed_list),
        "mean": mean(scores),
        "std": stddev(scores),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "worst": min(scores) if scores else 0.0,
        "best": max(scores) if scores else 0.0,
        "direct_mean": mean(direct_scores),
        "mirror_mean": mean(mirror_scores),
        "direct_std": stddev(direct_scores),
        "mirror_std": stddev(mirror_scores),
        "stderr": stderror(scores),
        "scores": scores,
    }


def to_file(path: Path, source: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding='utf-8')


def make_temp_bot(name: str, body: str):
    path = RESEARCH_DIR / f"{name}.py"
    to_file(path, f"""
# Name: Research Bot
# College: Research
# Roll Number: R-{name}

{body}
""")
    return str(path)


def write_result(name: str, payload: dict):
    path = RESULTS_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_template_with_policy(policy_name: str, strategy: str, extra: str = "") -> str:
    template = """
import random

class Bot:
    name = \"{policy_name}\"

    def reset(self, seat, config, seed):
        self.seat = seat
        self.config = config
        self.rng = random.Random(seed)
        self._anchor = {}

    def _value(self, obs, quote=None):
        if obs.is_maker or quote is None:
            return float(obs.k_mine + sum(obs.foresight))
        if obs.round not in self._anchor:
            if not obs.is_maker and quote is not None:
                self._anchor[obs.round] = (quote[0] + quote[1]) / 2
            else:
                self._anchor[obs.round] = 0.0
        anchor = self._anchor[obs.round]
        if obs.foresight:
            anchor = 0.5 * anchor + 0.5 * sum(obs.foresight)
        return float(anchor + obs.k_mine)

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        out = {}
        for name in offered:
            if name == \"TRANSFORM\":
                v = {strategy_expr}
            else:
                v = 0.0
            if v <= 0:
                continue
            fair_te = v / self.config.TE_SALVAGE
            bid_amount = max(0, min(int(fair_te * 0.6), obs.te_mine))
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
        if edge_buy > 0 and edge_buy >= edge_sell:
            return \"ACCEPT_BUY\"
        if edge_sell > 0:
            return \"ACCEPT_SELL\"
        w = max(0, (ask - bid) - self.config.MIN_REDUCTION)
        center = max(bid, min(round(v), ask - w))
        return (\"COUNTER\", center, center + w)

    def use_transform(self, obs):
        {extra_expr}
"""
    return template.replace("{policy_name}", policy_name).replace("{strategy_expr}", strategy).replace("{extra_expr}", extra)


def create_transform_policies():
    policies = {
        "never": read_template_with_policy("never", "0.0", "return False"),
        "always": read_template_with_policy("always", "2.0", "return True"),
        "denial_only": read_template_with_policy("denial_only", "0.0 if abs(obs.k_mine) > 1 else 0.0", "return abs(obs.k_mine) <= 1"),
        "flat_only": read_template_with_policy("flat_only", "1.5 if abs(obs.k_mine) <= 1 else 0.0", "return abs(obs.k_mine) <= 1"),
        "exercise_plus_denial": read_template_with_policy("exercise_plus_denial", "1.5 if abs(obs.k_mine) <= 1 else 0.6", "return abs(obs.k_mine) <= 1"),
        "state_cond": read_template_with_policy("state_cond", "1.5 if abs(obs.k_mine) <= 1 else 0.5 if abs(obs.te_mine - obs.te_theirs) <= 2 else 0.0", "return abs(obs.k_mine) <= 1"),
    }
    created = {}
    for name, code in policies.items():
        created[name] = make_temp_bot(f"transform_{name}", code)
    return created


def create_adaptive_variant(name: str, body: str):
    return make_temp_bot(name, body)


def build_dimension_bots():
    out = {}

    # A) TE economics policies
    out["te_fixed_reserve_8"] = create_adaptive_variant(
        "te_fixed_reserve_8",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-te-fixed8
from strategies.adaptive_bidder import Bot as BaseBot, SHADE

class Bot(BaseBot):
    name = "TEFixedReserve8"

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        reserve = 8
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
""",
    )

    out["te_linear_reserve"] = create_adaptive_variant(
        "te_linear_reserve",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-te-linear
from strategies.adaptive_bidder import Bot as BaseBot, SHADE

class Bot(BaseBot):
    name = "TELinearReserve"

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        reserve = max(0, 2 * (self.config.N_ROUNDS - obs.round))
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
""",
    )

    out["te_aggressive_early"] = create_adaptive_variant(
        "te_aggressive_early",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-te-agg
from strategies.adaptive_bidder import Bot as BaseBot, SHADE

class Bot(BaseBot):
    name = "TEAggressiveEarly"

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {}
        reserve = 0 if obs.round <= 2 else 6
        budget = max(0, obs.te_mine - reserve)
        shade = 0.75 if obs.round <= 2 else SHADE
        out = {}
        for name in offered:
            if budget <= 0:
                break
            v = self._transform_value(obs) if name == "TRANSFORM" else self._power_value(obs, name)
            if v <= 0:
                continue
            fair_te = v / self.config.TE_SALVAGE
            bid = max(0, min(int(fair_te * shade), budget))
            if bid > 0:
                out[name] = bid
                budget -= bid
        return out
""",
    )

    out["te_conservative_early"] = create_adaptive_variant(
        "te_conservative_early",
        """
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
""",
    )

    out["te_dynamic_power_slots"] = create_adaptive_variant(
        "te_dynamic_power_slots",
        """
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
""",
    )

    # B) Auction shading
    for shade in (0.35, 0.45, 0.55, 0.65, 0.75):
        tag = f"shade_{str(shade).replace('.', '_')}"
        out[tag] = create_adaptive_variant(
            tag,
            f"""
# Name: Research Bot
# College: Research
# Roll Number: R-{tag}
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "Shade{shade}"

    def bid(self, obs, offered):
        if not offered or obs.te_mine <= 0:
            return {{}}
        out = {{}}
        for name in offered:
            v = self._transform_value(obs) if name == "TRANSFORM" else self._power_value(obs, name)
            if v <= 0:
                continue
            fair_te = v / self.config.TE_SALVAGE
            bid_amount = max(0, min(int(fair_te * {shade}), obs.te_mine))
            out[name] = bid_amount
        return out
""",
        )

    # C) Power valuation conditionals
    out["value_round_te_cond"] = create_adaptive_variant(
        "value_round_te_cond",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-val-rte
from strategies.adaptive_bidder import Bot as BaseBot, POWER_VALUES

class Bot(BaseBot):
    name = "ValueRoundTECond"

    def _power_value(self, obs, name):
        base = POWER_VALUES.get(name, {}).get(obs.round, 0.5)
        te_ratio = obs.te_mine / max(1, self.config.TE_BUDGET)
        if name == "FORESIGHT":
            return base * (1.15 if obs.round >= 4 else 1.0)
        if name == "SUBSTITUTE":
            return base * (1.2 if obs.round <= 2 else 0.9)
        if name == "TRICK_ROOM":
            return base * (1.2 if te_ratio > 0.5 else 0.9)
        return base
""",
    )

    out["value_score_state"] = create_adaptive_variant(
        "value_score_state",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-val-score
from strategies.adaptive_bidder import Bot as BaseBot, POWER_VALUES

class Bot(BaseBot):
    name = "ValueScoreState"

    def _power_value(self, obs, name):
        base = POWER_VALUES.get(name, {}).get(obs.round, 0.5)
        flat = abs(obs.k_mine) <= 1
        if name == "TRANSFORM":
            return base * (1.2 if flat else 0.8)
        if name == "SUBSTITUTE":
            return base * (1.1 if not flat else 0.9)
        return base
""",
    )

    out["value_opponent_state"] = create_adaptive_variant(
        "value_opponent_state",
        """
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
""",
    )

    out["value_owned_power_interaction"] = create_adaptive_variant(
        "value_owned_power_interaction",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-val-own
from strategies.adaptive_bidder import Bot as BaseBot, POWER_VALUES

class Bot(BaseBot):
    name = "ValueOwnedPowerInteraction"

    def _power_value(self, obs, name):
        base = POWER_VALUES.get(name, {}).get(obs.round, 0.5)
        if "STEALTH_ROCK" in obs.powers_mine and name == "TRICK_ROOM":
            return base * 1.25
        if "SUBSTITUTE" in obs.powers_mine and name == "SUBSTITUTE":
            return base * 0.5
        return base
""",
    )

    # D) Transform policies
    out["xform_direct_only"] = create_adaptive_variant(
        "xform_direct_only",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-xf-direct
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "TransformDirectOnly"

    def _transform_value(self, obs):
        swap = self._power_value(obs, "TRANSFORM")
        return swap if abs(obs.k_mine) <= 1 else 0.0

    def use_transform(self, obs):
        return abs(obs.k_mine) <= 1
""",
    )

    out["xform_denial_only"] = create_adaptive_variant(
        "xform_denial_only",
        """
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
""",
    )

    out["xform_combined"] = create_adaptive_variant(
        "xform_combined",
        """
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
""",
    )

    out["xform_maker_interaction"] = create_adaptive_variant(
        "xform_maker_interaction",
        """
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
""",
    )

    out["xform_round_te_opp"] = create_adaptive_variant(
        "xform_round_te_opp",
        """
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
""",
    )

    # E) Negotiation policies
    out["nego_wide_quote"] = create_adaptive_variant(
        "nego_wide_quote",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-nego-wide
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoWideQuote"

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        cap = obs.spread_cap
        lo = v - cap // 2
        return (lo, lo + cap)
""",
    )

    out["nego_mid_width"] = create_adaptive_variant(
        "nego_mid_width",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-nego-mid
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoMidWidth"

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        w = (obs.final_cap + obs.spread_cap) // 2
        lo = v - w // 2
        return (lo, lo + w)
""",
    )

    out["nego_center_bias"] = create_adaptive_variant(
        "nego_center_bias",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-nego-bias
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoCenterBias"

    def quote(self, obs):
        v = round(obs.k_mine + sum(obs.foresight))
        bias = 1 if obs.is_maker else 0
        cap = obs.final_cap
        lo = (v + bias) - cap // 2
        return (lo, lo + cap)
""",
    )

    out["nego_aggressive_accept"] = create_adaptive_variant(
        "nego_aggressive_accept",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-nego-acc
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoAggressiveAccept"

    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = self._value(obs, quote)
        edge_buy = v - ask
        edge_sell = bid - v
        thresh = -0.5
        if "SUBSTITUTE" in obs.powers_mine:
            thresh -= 1.0
        if edge_buy > thresh and edge_buy >= edge_sell:
            return "ACCEPT_BUY"
        if edge_sell > thresh:
            return "ACCEPT_SELL"
        w = max(0, (ask - bid) - self.config.MIN_REDUCTION)
        center = max(bid, min(round(v), ask - w))
        return ("COUNTER", center, center + w)
""",
    )

    out["nego_final_turn_force_aware"] = create_adaptive_variant(
        "nego_final_turn_force_aware",
        """
# Name: Research Bot
# College: Research
# Roll Number: R-nego-force
from strategies.adaptive_bidder import Bot as BaseBot

class Bot(BaseBot):
    name = "NegoFinalTurnAware"

    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = self._value(obs, quote)
        edge_buy = v - ask
        edge_sell = bid - v
        if edge_buy > 0 and edge_buy >= edge_sell:
            return "ACCEPT_BUY"
        if edge_sell > 0:
            return "ACCEPT_SELL"
        if turn == self.config.N_TURNS:
            if v >= (bid + ask) / 2:
                return "ACCEPT_BUY"
            return "ACCEPT_SELL"
        w = max(0, (ask - bid) - self.config.MIN_REDUCTION)
        center = max(bid, min(round(v), ask - w))
        return ("COUNTER", center, center + w)
""",
    )

    return out


def create_adversarial_suite():
    out = {}
    out["adv_aggressive_bidder"] = make_temp_bot(
        "adv_aggressive_bidder",
        """
import random

class Bot:
    name = "AggressiveBidder"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        if not offered:
            return {}
        return {name: max(0, min(obs.te_mine // max(1, len(offered)), obs.te_mine)) for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        w = obs.final_cap
        return (v - w // 2, v + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = obs.k_mine
        if v > ask:
            return "ACCEPT_BUY"
        if v < bid:
            return "ACCEPT_SELL"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = max(bid, min(v, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) <= 2
""",
    )
    out["adv_conservative_bidder"] = make_temp_bot(
        "adv_conservative_bidder",
        """
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
""",
    )
    out["adv_wide_quote_maker"] = make_temp_bot(
        "adv_wide_quote_maker",
        """
import random

class Bot:
    name = "WideQuoteMaker"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        return {name: 1 for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        w = obs.spread_cap
        return (v - w // 2, v + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        if turn == self.config.N_TURNS:
            return "ACCEPT_BUY"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = (bid + ask) // 2
        c = max(bid, min(c, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) <= 1
""",
    )
    out["adv_min_width_maker"] = make_temp_bot(
        "adv_min_width_maker",
        """
import random

class Bot:
    name = "MinWidthMaker"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        return {name: 2 for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        w = obs.final_cap
        return (v - w // 2, v + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = obs.k_mine
        if v >= ask:
            return "ACCEPT_BUY"
        if v <= bid:
            return "ACCEPT_SELL"
        if turn == self.config.N_TURNS:
            return "ACCEPT_SELL"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = max(bid, min(v, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) == 0
""",
    )
    out["adv_deceptive_quote_maker"] = make_temp_bot(
        "adv_deceptive_quote_maker",
        """
import random

class Bot:
    name = "DeceptiveQuoteMaker"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        return {name: 1 for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        fake = v + (2 if v <= 0 else -2)
        w = obs.final_cap
        return (fake - w // 2, fake + (w - w // 2))
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
        return abs(obs.k_mine) <= 1
""",
    )
    out["adv_aggressive_counterer"] = make_temp_bot(
        "adv_aggressive_counterer",
        """
import random

class Bot:
    name = "AggressiveCounterer"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        return {name: 1 for name in offered}
    def quote(self, obs):
        v = obs.k_mine
        w = obs.final_cap
        return (v - w // 2, v + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        if turn == self.config.N_TURNS:
            return "COUNTER", bid, ask
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = (bid + ask) // 2
        c = max(bid, min(c, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) <= 1
""",
    )
    out["adv_transform_specialist"] = make_temp_bot(
        "adv_transform_specialist",
        """
import random

class Bot:
    name = "TransformSpecialist"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        out = {}
        for name in offered:
            if name == "TRANSFORM":
                out[name] = min(obs.te_mine, 12)
            else:
                out[name] = 1
        return out
    def quote(self, obs):
        v = obs.k_mine
        w = obs.final_cap
        return (v - w // 2, v + (w - w // 2))
    def respond(self, obs, quote, turn):
        bid, ask = quote
        v = obs.k_mine
        if v > ask:
            return "ACCEPT_BUY"
        if v < bid:
            return "ACCEPT_SELL"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = max(bid, min(v, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return abs(obs.k_mine) <= 2
""",
    )
    out["adv_randomized"] = make_temp_bot(
        "adv_randomized",
        """
import random

class Bot:
    name = "Randomized"
    def reset(self, seat, config, seed):
        self.config = config
        self.rng = random.Random(seed)
    def bid(self, obs, offered):
        out = {}
        rem = obs.te_mine
        for name in offered:
            b = self.rng.randint(0, rem) if rem > 0 else 0
            out[name] = b
            rem -= b
        return out
    def quote(self, obs):
        v = obs.k_mine + self.rng.choice([-1, 0, 1])
        w = self.rng.randint(obs.final_cap, obs.spread_cap)
        lo = v - w // 2
        return (lo, lo + w)
    def respond(self, obs, quote, turn):
        bid, ask = quote
        if self.rng.random() < 0.25:
            return "ACCEPT_BUY"
        if self.rng.random() < 0.25:
            return "ACCEPT_SELL"
        w = max(0, ask - bid - self.config.MIN_REDUCTION)
        c = self.rng.randint(bid, ask) if bid <= ask else bid
        c = max(bid, min(c, ask - w))
        return ("COUNTER", c, c + w)
    def use_transform(self, obs):
        return self.rng.random() < 0.5
""",
    )
    return out


def audit_transform(seed: int = 7):
    policies = create_transform_policies()
    rows = []
    probe_obs = Obs(
        seat=0,
        round=2,
        my_revealed=(1, -1, 1, -1),
        te_mine=12,
        te_theirs=12,
        spread_cap=9,
        final_cap=7,
        is_maker=True,
        powers_mine=frozenset(),
        powers_theirs=frozenset(),
        auction_log=(),
        contracts=(),
        foresight=(),
        n_unknown_both=20,
        n_turns=6,
    )
    flat_obs = Obs(
        seat=0,
        round=2,
        my_revealed=(1, -1, 1, -1),
        te_mine=10,
        te_theirs=10,
        spread_cap=9,
        final_cap=7,
        is_maker=True,
        powers_mine=frozenset({"TRANSFORM"}),
        powers_theirs=frozenset(),
        auction_log=(),
        contracts=(),
        foresight=(),
        n_unknown_both=20,
        n_turns=6,
    )
    decisive_obs = Obs(
        seat=0,
        round=2,
        my_revealed=(1, 1, 1, 1),
        te_mine=10,
        te_theirs=10,
        spread_cap=9,
        final_cap=7,
        is_maker=True,
        powers_mine=frozenset({"TRANSFORM"}),
        powers_theirs=frozenset(),
        auction_log=(),
        contracts=(),
        foresight=(),
        n_unknown_both=20,
        n_turns=6,
    )

    for name, path in policies.items():
        BotCls = load_bot_for_research(path)
        bot = BotCls()
        reset_ok = True
        reset_error = ""
        try:
            bot.reset(0, GameConfig(), seed)
        except Exception as e:
            reset_ok = False
            reset_error = f"{type(e).__name__}: {e}"
        bid_probe = {}
        use_probe = {}
        if reset_ok:
            bid_probe = bot.bid(probe_obs, ["TRANSFORM"])
            use_probe = {
                "flat_k0": bool(bot.use_transform(flat_obs)),
                "decisive_k4": bool(bot.use_transform(decisive_obs)),
            }
        rows.append({
            "policy": name,
            "path": path,
            "loaded_class": BotCls.__name__,
            "loaded_name": getattr(BotCls, "name", None),
            "reset_ok": reset_ok,
            "reset_error": reset_error,
            "bid_probe": bid_probe,
            "use_transform_probe": use_probe,
        })

    # Tiny deterministic behavioral proof: extreme A/B directly.
    # We only print transform-related action lines from official backtester logs.
    summary = summarize_pair(
        policies["never"],
        policies["always"],
        seeds=[seed],
        n_deals=1,
        mirror=True,
    )
    return {
        "seed": seed,
        "load_and_reset": rows,
        "never_vs_always": summary,
    }


def benchmark_baselines_100():
    seeds = list(range(100))
    pairs = [
        ("strategies/adaptive_bidder.py", "strategies/rational.py"),
        ("strategies/adaptive_bidder.py", "strategies/naive_ev.py"),
    ]
    out = {}
    for a, b in pairs:
        out[f"{Path(a).stem}_vs_{Path(b).stem}"] = summarize_pair(a, b, seeds, n_deals=10, mirror=True)
    return out


def sweep_vs_incumbent(candidates: dict[str, str], seeds: list[int], n_deals: int = 8):
    baseline = "strategies/adaptive_bidder.py"
    out = {}
    for name, path in candidates.items():
        out[name] = summarize_pair(path, baseline, seeds, n_deals=n_deals, mirror=True)
    return out


def sweep_opponents(candidate_path: str, opponents: dict[str, str], seeds: list[int], n_deals: int = 8):
    out = {}
    for name, opp_path in opponents.items():
        out[name] = summarize_pair(candidate_path, opp_path, seeds, n_deals=n_deals, mirror=True)
    return out


def pick_best(results: dict[str, dict]):
    items = list(results.items())
    if not items:
        return None
    items.sort(key=lambda kv: (kv[1]["mean"], -kv[1]["std"]), reverse=True)
    return items[0][0], items[0][1]


def run_full_research():
    report = {}

    report["audit_transform"] = audit_transform(seed=7)
    report["baseline_100"] = benchmark_baselines_100()

    dimension_bots = build_dimension_bots()
    dev_seeds = list(range(0, 80))
    val_seeds = list(range(100, 180))

    te_keys = [k for k in dimension_bots if k.startswith("te_")]
    shade_keys = [k for k in dimension_bots if k.startswith("shade_")]
    value_keys = [k for k in dimension_bots if k.startswith("value_")]
    xform_keys = [k for k in dimension_bots if k.startswith("xform_")]
    nego_keys = [k for k in dimension_bots if k.startswith("nego_")]

    te_dev = sweep_vs_incumbent({k: dimension_bots[k] for k in te_keys}, dev_seeds)
    shade_dev = sweep_vs_incumbent({k: dimension_bots[k] for k in shade_keys}, dev_seeds)
    value_dev = sweep_vs_incumbent({k: dimension_bots[k] for k in value_keys}, dev_seeds)
    xform_dev = sweep_vs_incumbent({k: dimension_bots[k] for k in xform_keys}, dev_seeds)
    nego_dev = sweep_vs_incumbent({k: dimension_bots[k] for k in nego_keys}, dev_seeds)

    report["te_dev"] = te_dev
    report["shade_dev"] = shade_dev
    report["value_dev"] = value_dev
    report["transform_dev"] = xform_dev
    report["negotiation_dev"] = nego_dev

    best_te = pick_best(te_dev)
    best_shade = pick_best(shade_dev)
    best_value = pick_best(value_dev)
    best_xform = pick_best(xform_dev)
    best_nego = pick_best(nego_dev)

    report["best_dimension_candidates"] = {
        "te": best_te,
        "shade": best_shade,
        "value": best_value,
        "transform": best_xform,
        "negotiation": best_nego,
    }

    selected_keys = [
        best_te[0] if best_te else None,
        best_shade[0] if best_shade else None,
        best_value[0] if best_value else None,
        best_xform[0] if best_xform else None,
        best_nego[0] if best_nego else None,
    ]
    selected_keys = [k for k in selected_keys if k is not None]
    selected_keys = list(dict.fromkeys(selected_keys))

    val_dimension = sweep_vs_incumbent({k: dimension_bots[k] for k in selected_keys}, val_seeds)
    report["dimension_validation_vs_incumbent"] = val_dimension

    adversaries = create_adversarial_suite()
    report["adversarial_suite"] = adversaries

    robust_dev = {}
    robust_val = {}
    for k in selected_keys:
        robust_dev[k] = sweep_opponents(dimension_bots[k], adversaries, dev_seeds, n_deals=6)
        robust_val[k] = sweep_opponents(dimension_bots[k], adversaries, val_seeds, n_deals=6)

    report["robustness_dev"] = robust_dev
    report["robustness_val"] = robust_val

    robust_scores = {}
    for k in selected_keys:
        vals = [robust_val[k][opp]["mean"] for opp in adversaries]
        worsts = [robust_val[k][opp]["worst"] for opp in adversaries]
        robust_scores[k] = {
            "avg_mean_across_adversaries": mean(vals),
            "worst_single_seed_result": min(worsts) if worsts else 0.0,
        }

    report["robust_scores"] = robust_scores
    report["strongest_candidate"] = pick_best({k: {"mean": v["avg_mean_across_adversaries"], "std": 0.0} for k, v in robust_scores.items()})

    return report


def run_baseline_suite(seeds=range(0, 30), n_deals=10):
    files = [
        "strategies/naive_ev.py",
        "strategies/rational.py",
        "strategies/adaptive_bidder.py",
    ]
    results = []
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            r = summarize_pair(files[i], files[j], seeds, n_deals=n_deals, mirror=True)
            results.append(r)
    return results


def print_stats(label, stats):
    print(f"\n=== {label} ===")
    print(f"mean={stats['mean']:.2f} std={stats['std']:.2f} worst={stats['worst']:.2f} best={stats['best']:.2f}")
    print(f"wins={stats['wins']} losses={stats['losses']} draws={stats['draws']} direct_mean={stats['direct_mean']:.2f} mirror_mean={stats['mirror_mean']:.2f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=["baseline", "transform", "audit_transform", "baseline100", "full_research"],
        default="baseline",
    )
    parser.add_argument("--seeds", type=int, default=30)
    args = parser.parse_args()

    if args.phase == "baseline":
        seeds = list(range(args.seeds))
        results = run_baseline_suite(seeds=seeds, n_deals=10)
        print("Baseline benchmark using engine.play_match() with seeds 0..%d" % (args.seeds - 1))
        for result in results:
            print_stats(f"{result['bot_a']} vs {result['bot_b']}", result)
        return

    if args.phase == "transform":
        policies = create_transform_policies()
        baseline = "strategies/adaptive_bidder.py"
        seeds = list(range(args.seeds))
        for name, path in policies.items():
            stats = summarize_pair(path, baseline, seeds, n_deals=10, mirror=True)
            print_stats(f"transform policy {name} vs {baseline}", stats)
        return

    if args.phase == "audit_transform":
        report = audit_transform(seed=7)
        out = write_result("audit_transform", report)
        print(json.dumps(report, indent=2))
        print(f"\nSaved: {out}")
        return

    if args.phase == "baseline100":
        report = benchmark_baselines_100()
        out = write_result("baseline100", report)
        for k, v in report.items():
            print_stats(k, v)
        print(f"\nSaved: {out}")
        return

    if args.phase == "full_research":
        report = run_full_research()
        out = write_result("full_research", report)
        print("Completed full research run.")
        print(f"Saved: {out}")
        return


if __name__ == "__main__":
    main()
