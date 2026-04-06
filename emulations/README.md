# Reactive SDN Emulation README

## Overview

This project emulates a reactive SDN forwarding setup using **two separate VMs**:

- a **Mininet VM** that runs the network topology, traffic generation, and traffic collection, and
- an **ONOS VM** that runs **ONOS 4.2.8** with the forwarding application source modified before startup.

The experiment is designed to study delay behavior under different offered traffic rates and different reactive forwarding idle timeouts.

At a high level, the workflow is:

1. Start ONOS on one VM after replacing the required forwarding application source files and setting the desired idle timeout.
2. Start the Mininet topology on the other VM and point it to the remote ONOS controller IP.
3. Emulate controller-switch transmission delay between the two VMs.
4. Run MGEN traffic from `h1` to `h2` over a sweep of packet rates.
5. Collect sender and receiver logs.
6. Run the post-processing script to generate:
   - `per_packet_delays.csv`
   - `avg_delay_per_rate.csv`

---

## Code Structure

## Mininet VM Files

### `Mininet_Script.py`

Purpose:
- Builds the Mininet topology.
- Connects the switch to a remote ONOS controller.
- Applies the switch-side netem rate limit.
- Provides the Mininet interactive session where traffic commands can be launched.

---

### `run_mgen_multiple_rates.sh`

Purpose:
- Sweeps through a range of packet rates.
- Generates one temporary MGEN input file per rate and stores it inside `mgen_tmp/`
- Runs MGEN for each rate.
- Stores a sender-side log per tested rate inside `logs/`

---

### `recv.mgn`

Purpose:
- Makes the receiver listen on the desired UDP port and saves the log in `mgm_recv.log`

---

### `compute_avg_delay_from_sendlogs.py`

Purpose:
- Parses the receiver log and the sender logs.
- Maps received packets back to the sender rate interval they belong to.
- Computes both per-packet delay and average delay per rate.
- Writes two CSV files: `per_packet_delays.csv` and `avg_delay_per_rate.csv`

---

## ONOS VM Files

### `ReactiveForwarding.java`

Purpose:
- This keeps the main reactive forwarding logic intact, while emulating controller-side delay and adding timing logs.

Briefly, compared with the original ONOS source, the main changes are:
- near the start of `process(PacketContext context)`, it introduces an approximately **500 ms pause** before the normal forwarding logic continues,
- it logs `"Missed packet"` when processing begins,
- it records `start_time`, `end_time`, and `elapsed`, then logs elapsed time at multiple early-return and normal-exit points in `process()`.

The modified `ReactiveForwarding.java` is being used to emulate a slower controller-side packet-miss handling process while also exposing elapsed processing time through ONOS log messages.

---

## File Placement

### Mininet VM
Copy the files from:

```text
Emulation Codes/Mininet VM Codes/
```

onto the Mininet VM.

### ONOS VM
Copy the ONOS-side source file(s) from:

```text
Emulation Codes/Onos VM Codes/
```

into the corresponding ONOS forwarding application source tree.

Based on your workflow, the relevant ONOS source paths are:

```text
~/onos/apps/fwd/src/main/java/org/onosproject/fwd/ReactiveForwarding.java
```

You stated that:

- `ReactiveForwarding.java` is replaced with your modified version before ONOS is run.
- `FLOW_TIMEOUT_DEFAULT` inside `OsgiPropertyConstants.java` is changed to the desired idle timeout value before ONOS is run.

---

## Configuration

### Configure the Remote ONOS Controller IP

In `Mininet_Script.py`, update the controller IP before running. Replace this with the IP address of your ONOS VM.

---

### Set the Desired Idle Timeout in ONOS

Before starting ONOS, edit:

```text
~/onos/apps/fwd/src/main/java/org/onosproject/fwd/OsgiPropertyConstants.java
```

and change:

```java
static final int FLOW_TIMEOUT_DEFAULT
```

to the idle timeout value you want to test.

This means that **each idle-timeout experiment** should be run after updating this constant and then starting ONOS with that value.

---

### Replace the Forwarding Application Source on the ONOS VM

Before running ONOS, replace:

```text
~/onos/apps/fwd/src/main/java/org/onosproject/fwd/ReactiveForwarding.java
```

with your modified forwarding source.

---

### Configure Controller-Switch Propagation Delay

To emulate transmission delay between the Mininet VM and ONOS VM, apply the following command on **both VMs**:

```bash
sudo tc qdisc add dev {YOUR INTERFACE} root netem delay {YOUR DELAY}
```

---

### Configure the Switch-Side Processing Rate

Inside `Mininet_Script.py`, the script also applies a rate-limiting qdisc to the switch egress interface facing `h2`:

```python
s1.cmd('tc qdisc replace dev s1-eth2 root netem rate 24kbit limit 100000')
```

This is used to emulate a switch-side service/processing bottleneck.

A practical approximation is:

```text
rate (bits/s) ≈ packet_size_bytes × 8 × desired_max_pps
```

---

## Running the Emulation

### Step 1 — Start ONOS on the ONOS VM

Before starting ONOS:

1. Replace `ReactiveForwarding.java` with the modified version.
2. Edit `OsgiPropertyConstants.java` and set `FLOW_TIMEOUT_DEFAULT` to the idle timeout you want.

Then run ONOS using your normal ONOS build/start workflow.

---

### Step 2 — Start Mininet on the Mininet VM

Run:

```bash
python Mininet_Script.py
```

This script:

- creates a topology with `h1`, `s1`, and `h2`,
- connects `s1` to the remote ONOS controller, and
- applies the netem rate limit on `s1-eth2`.

---

### Step 3 — Start the Receiver on `h2`

Run `recv.mgn` inside host `h2` with

```bash
mgen input recv.mgn &> mgm_recv.log
```

This creates the **receiver log** that will later be parsed by the post-processing script.

---

### Step 4 — Run the Sender Sweep on `h1`

Run:

```bash
./run_mgen_multiple_rates.sh
```

This script generates Poisson traffic from `h1` to `h2` across a configurable rate range.

You can control the experiment sweep by editing the following fields near the top of the script:

- `START_RATE`
- `END_RATE`
- `STEP`
- `DURATION`

---

## Experiment Summary

A typical experiment for one idle-timeout value looks like this:

1. On the ONOS VM:
   - replace `ReactiveForwarding.java`,
   - set `FLOW_TIMEOUT_DEFAULT` in `OsgiPropertyConstants.java`,
   - start ONOS.
2. On both VMs:
   - apply transmission delay on the correct egress interface.
3. On the Mininet VM:
   - update the remote controller IP in `Mininet_Script.py`,
   - run `python Mininet_Script.py`.
4. In Mininet:
   - run the receiver on `h2` using `recv.mgn`,
   - run `run_mgen_multiple_rates.sh` on `h1`.
5. After the traffic sweep ends:
   - run `compute_avg_delay_from_sendlogs.py` in the experiment directory to get the results.

Repeat the same process for each idle timeout you want to evaluate.

---

## Notes

- The controller IP in `Mininet_Script.py` must be updated before running the topology.
- The interface name in the `tc qdisc add dev ...` command must match the actual egress interface on each VM.
- The switch-side `netem rate` should be selected consistently with packet size and the desired maximum packets-per-second ceiling.
- `ReactiveForwarding.java` in this code set adds a fixed delay and elapsed-time logging inside `process()`, while preserving the underlying reactive forwarding flow.

---
