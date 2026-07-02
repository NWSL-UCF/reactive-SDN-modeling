# Reactive SDN Modeling

This repository is organized into three main parts:

- `simulations/` - discrete-event simulation code, parameter sweeps, and plotting scripts.
- `emulations/` - emulation-related code and experiments.
- `analytical/` - analytical models and closed-form delay analysis.

## How to navigate

Start here depending on what you want:

- If you want to **run simulations**, go to `simulations/`.
- If you want to **study analytical results or formulas**, go to `analytical/`.
- If you want to **run emulation experiments**, go to `emulations/`.
- If you want to **study the idle-timeout vs. TCAM occupancy trade-off** on a campus network PCAP, go to `idle_timeout_and_TCAM_occupancy_tradeoff_experiment/`.

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

Mininet + ONOS emulation setup for reactive forwarding delay under different traffic rates and idle timeouts.

- `emulations/README.md` - setup, configuration, and run instructions for the two-VM workflow.
- `emulations/1. Mininet VM Codes/` - topology, MGEN traffic sweep, and delay post-processing.
- `emulations/2. Onos VM Codes/` - modified `ReactiveForwarding.java` for controller-side delay logging.
- `emulations/3. Results/` - analytical and simulation comparison CSVs.

### `idle_timeout_and_TCAM_occupancy_tradeoff_experiment/`

Trace-driven study of TCAM/SFT occupancy vs. idle timeout on a campus network PCAP (`trace_1`).

> **Disclaimer:** The original campus network packet trace (PCAP) is not included in this repository and may not be shared or redistributed for security and data-use reasons. What is shared here are simulation outputs only: the **number of active flow-table entries (TCAM/SFT occupancy)**, sampled over time and summarized per idle timeout — no packet payloads, IP addresses, or per-flow identifiers.

- `idle_timeout_and_TCAM_occupancy_tradeoff_experiment/readme.md` - experiment overview, data layout, and regenerate commands.
- `idle_timeout_and_TCAM_occupancy_tradeoff_experiment/scripts/` - PCAP-to-SFT simulation and plotting scripts.
- `idle_timeout_and_TCAM_occupancy_tradeoff_experiment/data/` - TCAM occupancy time series and summary CSVs (Δ ∈ {1, 2, 3, 4, 5, 10} s).
- `idle_timeout_and_TCAM_occupancy_tradeoff_experiment/figures/` - comparison plots (PNG and PDF).

## Recommended reading order
1. Check `analytical/` for the analytical model behind the results.
2. Read `simulations/README.md` for how to run the simulator.
3. Read `emulations/README.md` for how to run the Mininet/ONOS emulation.
4. See `idle_timeout_and_TCAM_occupancy_tradeoff_experiment/readme.md` for the idle-timeout vs. TCAM occupancy trade-off on `trace_1`.
