# trace_1 TCAM Idle Timeout Trade-off

Campus network access-switch PCAP (`trace_1`).  
**Duration:** ~5.2 min (312 s).

## Disclaimer

The original campus network packet trace (PCAP) is **not** included in this repository and may not be shared or redistributed for security and data-use reasons. Traffic captures may contain sensitive metadata and are subject to data-use restrictions.

What is shared in this folder are **simulation outputs only**: the **number of active flow-table entries (TCAM/SFT occupancy)**, sampled every 1 s throughout the trace, for each idle timeout Δ ∈ {1, 2, 3, 4, 5, 10} s. No packet payloads, IP addresses, or per-flow identifiers are included.

## Contents

### `figures/`

| File | Description |
|------|-------------|
| `trace_1_tcam_idle_timeout_comparison.png` | Final plot (box plots + delay gap) |
| `trace_1_tcam_idle_timeout_comparison.pdf` | Final plot (PDF) |

### `data/`

| File | Description |
|------|-------------|
| `trace_1_sft_idle{N}s_int1s.csv` | Simulated TCAM occupancy time series (N = 1, 2, 3, 4, 5, 10 s idle timeout; sampled every 1 s) |
| `trace_1_tcam_idle_timeout_summary.csv` | Median/mean occupancy and delay gap per idle timeout |

### `scripts/`

| File | Description |
|------|-------------|
| `simulate_sft_from_pcap.py` | Generate SFT occupancy CSVs from a local PCAP (not included in this repo) |
| `plot_tcam_idle_timeout_comparison.py` | Generate the comparison figure |

## Regenerate figure

From the repository root, using the published occupancy CSVs in `data/`:

```bash
python3 idle_timeout_and_TCAM_occupancy_tradeoff_experiment/scripts/plot_tcam_idle_timeout_comparison.py \
  --raw-dir idle_timeout_and_TCAM_occupancy_tradeoff_experiment/data \
  --stem trace_1 \
  -o idle_timeout_and_TCAM_occupancy_tradeoff_experiment/figures/trace_1_tcam_idle_timeout_comparison.png
```

## Regenerate simulation CSVs (from PCAP)

Requires a local copy of the source PCAP (not distributed with this repository):

```bash
python3 idle_timeout_and_TCAM_occupancy_tradeoff_experiment/scripts/simulate_sft_from_pcap.py \
  /path/to/trace.pcap --idle-timeout 5 --interval 1 \
  -o idle_timeout_and_TCAM_occupancy_tradeoff_experiment/data/trace_1_sft_idle5s_int1s.csv
```

> **Note:** Delay gap uses analytical \(E[D](\Delta)\); \(E[D]^* = 0.50\) s at \(\Delta = 10\) s.
