# QuantStorm 2026: Algorithmic Trading Agent

**Author:** Moinak Goswami | Indian Institute of Technology Ropar

## Overview
This repository contains my quantitative research framework and final algorithmic trading agent developed for QuantStorm 2026 (Round 1). The competition centers on a two-player market game involving hidden-score estimation, Bayesian inference, first-price auctions, and intertemporal resource allocation (Tactical Energy).

Rather than relying on heuristic guessing, I built an isolated, Monte Carlo-based backtesting harness to rigorously evaluate strategy hypotheses. The final agent is the product of isolating specific strategic levers, verifying them across 100-seed validation blocks, and testing them against custom adversarial bots to ensure robust out-of-sample performance.

## Quantitative Research Methodology

The development process was strictly empirical, consisting of three phases:

1. **Harness Integrity & Anomaly Resolution:** 
   Early simulations identified a statistical anomaly where all variants of a specific power (`TRANSFORM`) produced identical PnL. I traced this to a state-reset bug in the underlying game engine's interaction with the research bots. Patching the harness to isolate state per deal allowed for accurate strategy measurement.
2. **Variable Isolation & Measurement:** 
   Baseline testing established `adaptive_bidder` as the strongest incumbent. I independently measured the marginal PnL impact of specific levers across 100 independent seeds.
3. **Adversarial Validation:** 
   To prevent overfitting, candidate policies were stress-tested against a suite of 8 custom adversarial agents (e.g., aggressive bidders, deceptive quote makers).

## Key Strategic Discoveries (Alpha Sources)

Through large-scale simulation, three statistically significant edges were isolated and implemented into the final `CandidateBot`:

* **Final-Turn Forcing Awareness (+17.36 Mean PnL):** 
  The dominant strategic lever. Optimized the negotiation threshold logic to account for final-turn forcing economics, maximizing spread capture when acting as the Maker.
* **Auction Bidding Shading (+1.51 Mean PnL):** 
  Identified a ~0.65 bid multiplier as the optimal shading parameter for Tactical Energy (TE) allocation in simultaneous first-price auctions, balancing power acquisition against opportunity cost.
* **Opponent-State Power Valuation (+1.64 Mean PnL):** 
  Shifted from static power valuation to a state-conditioned model. The bot dynamically values powers like `FORESIGHT` and `TRANSFORM` based on the opponent's inferred score state from previous quote leakage.
* *Rejected Hypotheses:* Extensive testing proved that complex dynamic TE reserves and heavy `TRANSFORM` denial strategies failed to robustly outperform the incumbent's baseline logic, and were thus excluded to prevent catastrophic downside risk.

## Repository Structure

* **`research_framework.py`**: The custom Monte Carlo benchmark harness used to run large-seed validations without contaminating the official engine.
* **`research_bots/`**: Contains the adversarial testing suite and the final isolated `candidate_bot.py`.
* **`research_results/`**: Machine-readable JSON logs of the 100-seed baseline tests, transform audits, and validation sweeps.
* **`candidate_bot.py`**: The final, self-contained Python trading agent submitted to the competition. Implemented strictly without external dependencies to comply with isolated runtime constraints.

## Reproduction & Execution

To run the final candidate bot in a 100-seed isolated evaluation against the strongest baseline:

```bash
python backtester.py --bot1 research_bots/candidate_bot.py --bot2 strategies/adaptive_bidder.py --n_deals 100 --seed 42 --mirror --isolate