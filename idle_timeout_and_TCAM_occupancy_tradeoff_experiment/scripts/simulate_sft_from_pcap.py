#!/usr/bin/env python3
"""
Simulate Switch Flow Table (SFT) size over time from a PCAP capture.

Models an OpenFlow switch that installs a flow rule per directional
(ip_src, ip_dst) pair on first match and refreshes the rule's idle timer on
each subsequent match. A flow is removed when no matching packet arrives for
longer than the configured idle timeout.

The PCAP is replayed in capture order. At each sampling interval the script
expires idle flows, then records the number of active flow-table entries.

Output CSV columns: time_s, sft_size
  time_s   - seconds from the first packet in the trace
  sft_size - active flow count after idle expiry at that sample time
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
import time
from pathlib import Path

_PCAP_LE = 0xA1B2C3D4
_PCAP_BE = 0xD4C3B2A1
_PCAP_NS_LE = 0xA1B23C4D
_PCAP_NS_BE = 0x4D3CB2A1

_PROGRESS_INTERVAL = 500_000


def _eth_payload_offset(raw: bytes) -> tuple[int, int] | None:
    if len(raw) < 14:
        return None
    offset = 12
    eth_type = struct.unpack_from("!H", raw, offset)[0]
    offset += 2
    while eth_type == 0x8100:
        if len(raw) < offset + 4:
            return None
        eth_type = struct.unpack_from("!H", raw, offset + 2)[0]
        offset += 4
    return offset, eth_type


def extract_ipv4_endpoints(raw: bytes) -> tuple[str, str] | None:
    parsed = _eth_payload_offset(raw)
    if parsed is None:
        return None
    offset, eth_type = parsed
    if eth_type != 0x0800:
        return None
    if len(raw) < offset + 20:
        return None
    if (raw[offset] >> 4) != 4:
        return None
    ihl = (raw[offset] & 0x0F) * 4
    if ihl < 20 or len(raw) < offset + ihl:
        return None
    src = ".".join(str(b) for b in raw[offset + 12 : offset + 16])
    dst = ".".join(str(b) for b in raw[offset + 16 : offset + 20])
    return src, dst


def iter_pcap_packets(path: Path):
    """Yield (relative_time_s, raw_frame) from a libpcap file."""
    with open(path, "rb") as f:
        gh = f.read(24)
        if len(gh) < 24:
            raise ValueError(f"Truncated pcap global header: {path}")

        magic = struct.unpack("<I", gh[:4])[0]
        if magic in (_PCAP_LE, _PCAP_NS_LE):
            endian = "<"
            ts_div = 1_000_000.0 if magic == _PCAP_LE else 1_000_000_000.0
        elif magic in (_PCAP_BE, _PCAP_NS_BE):
            endian = ">"
            ts_div = 1_000_000.0 if magic == _PCAP_BE else 1_000_000_000.0
        else:
            raise ValueError(f"Unsupported pcap magic in {path}: 0x{magic:08x}")

        ph_fmt = endian + "IIII"
        t0: float | None = None

        while True:
            ph = f.read(16)
            if not ph:
                break
            if len(ph) < 16:
                raise ValueError(f"Truncated packet header in {path}")
            ts_sec, ts_frac, incl_len, _orig_len = struct.unpack(ph_fmt, ph)
            raw = f.read(incl_len)
            if len(raw) < incl_len:
                raise ValueError(f"Truncated packet data in {path}")

            ts = ts_sec + ts_frac / ts_div
            if t0 is None:
                t0 = ts
            yield ts - t0, raw


def expire_idle(
    flows: dict[tuple[str, str], float], now_s: float, idle_timeout_s: float
) -> None:
    expired = [k for k, last_seen in flows.items() if (now_s - last_seen) > idle_timeout_s]
    for k in expired:
        del flows[k]


def record_samples_until(
    flows: dict[tuple[str, str], float],
    samples: list[tuple[float, int]],
    next_sample_s: float,
    until_s: float,
    interval_s: float,
    idle_timeout_s: float,
) -> float:
    """Expire idle flows and append SFT-size samples for each interval <= until_s."""
    while next_sample_s <= until_s:
        expire_idle(flows, next_sample_s, idle_timeout_s)
        samples.append((next_sample_s, len(flows)))
        next_sample_s += interval_s
    return next_sample_s


def simulate_sft(
    pcap_path: Path,
    idle_timeout_s: float,
    interval_s: float,
    *,
    verbose: bool = True,
) -> tuple[list[tuple[float, int]], int, int]:
    """
    Replay pcap_path and return (samples, packets_read, packets_with_ip).

    samples: list of (time_s, sft_size) at each interval boundary.
    """
    flows: dict[tuple[str, str], float] = {}
    samples: list[tuple[float, int]] = []
    next_sample_s = 0.0
    packets_read = 0
    packets_with_ip = 0
    last_t = 0.0

    for t_s, raw in iter_pcap_packets(pcap_path):
        packets_read += 1
        last_t = t_s

        if packets_read % _PROGRESS_INTERVAL == 0 and verbose:
            print(
                f"  progress: packets={packets_read:,} samples={len(samples):,} "
                f"sft_size={len(flows):,} t={t_s:.1f}s",
                flush=True,
            )

        next_sample_s = record_samples_until(
            flows, samples, next_sample_s, t_s, interval_s, idle_timeout_s
        )

        endpoints = extract_ipv4_endpoints(raw)
        if endpoints is None:
            continue

        packets_with_ip += 1
        flows[endpoints] = t_s

    if packets_read == 0:
        samples.append((0.0, 0))
        return samples, 0, 0

    record_samples_until(
        flows, samples, next_sample_s, last_t, interval_s, idle_timeout_s
    )
    return samples, packets_read, packets_with_ip


def default_output_path(pcap_path: Path, idle_timeout_s: float, interval_s: float) -> Path:
    timeout_tag = f"{idle_timeout_s:g}".replace(".", "p")
    interval_tag = f"{interval_s:g}".replace(".", "p")
    return pcap_path.with_name(
        f"{pcap_path.stem}_sft_idle{timeout_tag}s_int{interval_tag}s.csv"
    )


def write_samples_csv(
    output_csv: Path,
    samples: list[tuple[float, int]],
    *,
    pcap_path: Path,
    idle_timeout_s: float,
    interval_s: float,
    packets_read: int,
    packets_with_ip: int,
) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["# pcap", pcap_path.name])
        writer.writerow(["# idle_timeout_s", f"{idle_timeout_s:g}"])
        writer.writerow(["# interval_s", f"{interval_s:g}"])
        writer.writerow(["# packets_read", packets_read])
        writer.writerow(["# packets_with_ipv4", packets_with_ip])
        writer.writerow([])
        writer.writerow(["time_s", "sft_size"])
        for t_s, size in samples:
            writer.writerow([f"{t_s:.6f}", size])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate SFT size over time from a PCAP (directional ip_src,ip_dst flows)."
    )
    parser.add_argument(
        "--pcap-path",
        type=Path,
        required=True,
        help="Input PCAP file",
    )
    parser.add_argument(
        "--idle-timeout",
        type=float,
        required=True,
        metavar="SECONDS",
        help="Flow idle timeout in seconds",
    )
    parser.add_argument(
        "--interval",
        type=float,
        required=True,
        metavar="SECONDS",
        help="Sampling interval in seconds (SFT size recorded every interval)",
    )
    parser.add_argument(
        "-o",
        "--output-csv",
        type=Path,
        default=None,
        help="Output CSV path (default: <pcap_stem>_sft_idle<timeout>s_int<interval>s.csv)",
    )
    args = parser.parse_args()

    pcap_path = args.pcap_path.resolve()
    if not pcap_path.is_file():
        print(f"PCAP not found: {pcap_path}", file=sys.stderr)
        sys.exit(1)
    if args.idle_timeout < 0:
        print("--idle-timeout must be >= 0", file=sys.stderr)
        sys.exit(1)
    if args.interval <= 0:
        print("--interval must be > 0", file=sys.stderr)
        sys.exit(1)

    output_csv = args.output_csv or default_output_path(
        pcap_path, args.idle_timeout, args.interval
    )

    print(
        f"Simulating SFT: pcap={pcap_path.name} "
        f"idle_timeout={args.idle_timeout}s interval={args.interval}s",
        flush=True,
    )
    t0 = time.perf_counter()
    samples, packets_read, packets_with_ip = simulate_sft(
        pcap_path,
        args.idle_timeout,
        args.interval,
    )
    elapsed = time.perf_counter() - t0

    write_samples_csv(
        output_csv,
        samples,
        pcap_path=pcap_path,
        idle_timeout_s=args.idle_timeout,
        interval_s=args.interval,
        packets_read=packets_read,
        packets_with_ip=packets_with_ip,
    )

    max_sft = max((s for _, s in samples), default=0)
    print(f"Wrote: {output_csv}", flush=True)
    print(
        f"  packets_read={packets_read:,} packets_with_ipv4={packets_with_ip:,} "
        f"samples={len(samples):,} max_sft_size={max_sft:,} elapsed={elapsed:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
