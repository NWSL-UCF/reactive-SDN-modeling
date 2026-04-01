# Reactive SDN Modeling

This repository is organized into three main parts:

- `simulations/` - discrete-event simulation code, parameter sweeps, and plotting scripts.
- `emulations/` - emulation-related code and experiments.
- `analytical/` - analytical models and closed-form delay analysis.

## How to navigate

Start here depending on what you want:

- If you want to **run simulations**, go to `simulations/`.
- If you want to **study analytical results or formulas**, go to `analytical/`.
- If you want to **work on emulation experiments**, go to `emulations/`.

## Folder guide

### `simulations/`

Contains the main simulator and helper scripts for sweeps and plots.

- `simulations/sim.py` - core simulation.
- `simulations/sweep_lambda.py` - sweep over arrival rate `λ`.
- `simulations/sweep_timeout.py` - sweep over idle timeout `Δ`.
- `simulations/optimal_timeout.py` - compute the optimal `Δ*`.
- `simulations/README.md` - detailed instructions for running simulation scripts.

### `analytical/`

Contains analytical derivations and scripts for delay components.

- `analytical/analytical_delay_components.py` - analytical `E[D]` and component breakdown.

### `emulations/`

Reserved for emulation workflows, scripts, results, and documentation.

## Recommended reading order
1. Check `analytical/` for the analytical model behind the results.
2. Read `simulations/README.md` for how to run the simulator.
3. Use `emulations/` when emulation artifacts are added.
