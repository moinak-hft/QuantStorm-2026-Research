
# Name: Research Bot
# College: Research
# Roll Number: R-value_owned_power_interaction


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

