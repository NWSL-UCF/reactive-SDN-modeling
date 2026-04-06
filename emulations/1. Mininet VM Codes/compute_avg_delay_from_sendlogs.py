#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compute_avg_delay_from_sendlogs.py

Compatibility: Python 2.7 and Python 3.x

Parses an MGEN receiver log and sender logs (send_<rate>pps.log) in a logs/ folder
and produces two CSV files:
  - avg_delay_per_rate.csv  (one row per rate)
  - per_packet_delays.csv   (one row per received packet)

Usage:
  1. Place this script in the directory containing your recv log (e.g. mgen_recv.log)
     and the `logs/` subdirectory with files named like `send_2.8pps.log`.
  2. Run:
       python compute_avg_delay_from_sendlogs.py --dir /path/to/experiment
     or, if you're in that directory:
       python compute_avg_delay_from_sendlogs.py

This version is compatible with Python 2.7 and Python 3.x.
"""
from __future__ import print_function
import os
import re
import argparse
import csv
import math
import sys
from datetime import datetime, timedelta

PY3 = sys.version_info[0] >= 3

# ---------- helpers ----------
def parse_time_hmsus(timestr):
    try:
        return datetime.strptime(timestr, "%H:%M:%S.%f")
    except ValueError:
        return datetime.strptime(timestr, "%H:%M:%S")

def find_recv_file(dirpath):
    candidates = ["mgm_recv.log", "recv.log", "mgen_recv.drc", "recv.drc"]
    for c in candidates:
        p = os.path.join(dirpath, c)
        if os.path.isfile(p):
            return p
    # fallback: pick first file that contains "RECV" lines
    for fname in os.listdir(dirpath):
        p = os.path.join(dirpath, fname)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r") as f:
                for _ in range(200):
                    line = f.readline()
                    if not line:
                        break
                    if "RECV" in line and "sent>" in line:
                        return p
        except Exception:
            continue
    return None

def read_mgen_start_time_from_log(logpath):
    start_re = re.compile(r"^(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+START")
    with open(logpath, "r") as f:
        for line in f:
            m = start_re.search(line)
            if m:
                return parse_time_hmsus(m.group(1))
    return None

def parse_recv_entries(recv_path):
    # return list of dicts: {'seq':int,'recv_dt':datetime,'sent_dt':datetime,'raw':line}
    sent_re = re.compile(r"sent>(\d{2}:\d{2}:\d{2}(?:\.\d+)?)")
    seq_re = re.compile(r"seq>(\d+)")
    entries = []
    with open(recv_path, "r") as f:
        for line in f:
            if "RECV" not in line:
                continue
            parts = line.strip().split()
            if not parts:
                continue
            recv_ts = parts[0]
            m_sent = sent_re.search(line)
            m_seq = seq_re.search(line)
            if not m_sent:
                continue
            sent_ts = m_sent.group(1)
            try:
                recv_dt = parse_time_hmsus(recv_ts)
                sent_dt = parse_time_hmsus(sent_ts)
            except Exception:
                continue
            seq = int(m_seq.group(1)) if m_seq else None
            entries.append({'seq': seq, 'recv_dt': recv_dt, 'sent_dt': sent_dt, 'raw': line.strip()})
    return entries

def parse_on_off_from_sendlog(path):
    """Return (on_dt, off_dt) as time-of-day datetimes (no date) if found, else (None,None)."""
    on_re = re.compile(r"^(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+ON\b")
    off_re = re.compile(r"^(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+OFF\b")
    on = None
    off = None
    with open(path, "r") as f:
        for line in f:
            m_on = on_re.search(line)
            m_off = off_re.search(line)
            if m_on and not on:
                on = parse_time_hmsus(m_on.group(1))
            if m_off and not off:
                off = parse_time_hmsus(m_off.group(1))
    return on, off

def build_intervals_from_sendlogs(logs_dir, recv_start_dt):
    """
    For each send_*.log, get (on_time_of_day, off_time_of_day) and convert to absolute datetimes
    using recv_start_dt's date as baseline. Returns list of tuples (on_abs, off_abs, rate, filename)
    """
    intervals = []
    ptn = re.compile(r"send[_-]?([0-9]+(?:\.[0-9]+)?)pps", re.IGNORECASE)
    for fname in os.listdir(logs_dir):
        m = ptn.search(fname)
        if not m:
            continue
        try:
            rate = float(m.group(1))
        except Exception:
            continue
        path = os.path.join(logs_dir, fname)
        on, off = parse_on_off_from_sendlog(path)
        if not on:
            # no ON line found; skip
            continue
        # convert on and off to absolute datetimes using recv_start_dt's date as baseline
        on_abs = on.replace(year=recv_start_dt.year, month=recv_start_dt.month, day=recv_start_dt.day)
        if off:
            off_abs = off.replace(year=recv_start_dt.year, month=recv_start_dt.month, day=recv_start_dt.day)
        else:
            off_abs = on_abs + timedelta(days=1)  # fallback large
        # if off before on, assume it wrapped midnight -> add 1 day to off
        if off_abs < on_abs:
            off_abs += timedelta(days=1)
        intervals.append((on_abs, off_abs, rate, fname))
    # sort intervals by start time
    intervals.sort(key=lambda x: x[0])
    return intervals

def mean(lst):
    return sum(lst) / float(len(lst)) if lst else 0.0

def pstdev(lst):
    if not lst:
        return 0.0
    if len(lst) == 1:
        return 0.0
    m = mean(lst)
    var = sum((x - m) ** 2 for x in lst) / float(len(lst))
    return math.sqrt(var)

def map_recv_entries_to_rates(recv_entries, intervals, recv_start_dt):
    """
    For each recv entry, map it to an interval by comparing its sent time-of-day (with date applied)
    to interval windows. Returns:
      per_rate_delays: dict rate -> list of delays (float seconds)
      per_packet_rows: list of dicts for per-packet CSV
      unknown_entries: list of recv entries not mapped
    """
    per_rate_delays = {}
    per_packet_rows = []
    unknown = []

    for e in recv_entries:
        sent_dt = e['sent_dt']
        recv_dt = e['recv_dt']
        # convert sent_dt to candidate absolute datetime using same date as recv_start_dt
        candidate_sent = sent_dt.replace(year=recv_start_dt.year, month=recv_start_dt.month, day=recv_start_dt.day)
        assigned = False
        for (on_abs, off_abs, rate, fname) in intervals:
            cs = candidate_sent
            # if cs < on_abs - 12h, add a day
            if cs + timedelta(hours=12) < on_abs:
                cs += timedelta(days=1)
            if cs >= on_abs and cs < off_abs:
                # assign
                cr = recv_dt.replace(year=on_abs.year, month=on_abs.month, day=on_abs.day)
                if cr + timedelta(hours=12) < cs:
                    cr += timedelta(days=1)
                delay = (cr - cs).total_seconds()
                per_rate_delays.setdefault(rate, []).append(delay)
                per_packet_rows.append({'rate': rate, 'seq': e['seq'], 'sent_time': cs.isoformat(), 'recv_time': cr.isoformat(), 'delay_s': delay, 'raw': e['raw'], 'send_log': fname})
                assigned = True
                break
        if not assigned:
            unknown.append(e)
    return per_rate_delays, per_packet_rows, unknown

def write_csvs(out_dir, per_rate_delays, per_packet_rows):
    avg_out = os.path.join(out_dir, "avg_delay_per_rate.csv")
    per_packet_out = os.path.join(out_dir, "per_packet_delays.csv")

    # avg csv
    if PY3:
        with open(avg_out, "w", newline='') as csvf:
            w = csv.writer(csvf)
            w.writerow(["rate_pps", "packet_count", "avg_delay_s", "std_delay_s", "min_delay_s", "max_delay_s"])
            for rate in sorted(per_rate_delays.keys()):
                d = per_rate_delays[rate]
                cnt = len(d)
                avg = mean(d)
                std = pstdev(d)
                w.writerow(["{:.3f}".format(rate), cnt, "{:.6f}".format(avg), "{:.6f}".format(std), "{:.6f}".format(min(d) if d else 0.0), "{:.6f}".format(max(d) if d else 0.0)])
    else:
        with open(avg_out, "wb") as csvf:
            w = csv.writer(csvf)
            w.writerow(["rate_pps", "packet_count", "avg_delay_s", "std_delay_s", "min_delay_s", "max_delay_s"])
            for rate in sorted(per_rate_delays.keys()):
                d = per_rate_delays[rate]
                cnt = len(d)
                avg = mean(d)
                std = pstdev(d)
                # Ensure values are bytes/str for Python2 csv
                w.writerow(["{:.3f}".format(rate).encode('utf-8'), str(cnt).encode('utf-8'),
                            "{:.6f}".format(avg).encode('utf-8'), "{:.6f}".format(std).encode('utf-8'),
                            "{:.6f}".format(min(d) if d else 0.0).encode('utf-8'),
                            "{:.6f}".format(max(d) if d else 0.0).encode('utf-8')])

    # per-packet csv
    if PY3:
        with open(per_packet_out, "w", newline='') as csvf:
            w = csv.writer(csvf)
            w.writerow(["rate_pps", "seq", "sent_time", "recv_time", "delay_s", "send_log", "raw_recv_line"])
            for r in per_packet_rows:
                w.writerow(["{:.3f}".format(r['rate']), r['seq'], r['sent_time'], r['recv_time'], "{:.6f}".format(r['delay_s']), r['send_log'], r['raw']])
    else:
        with open(per_packet_out, "wb") as csvf:
            w = csv.writer(csvf)
            w.writerow(["rate_pps", "seq", "sent_time", "recv_time", "delay_s", "send_log", "raw_recv_line"])
            for r in per_packet_rows:
                raw = r['raw']
                try:
                    raw_enc = raw.encode('utf-8')
                except Exception:
                    raw_enc = raw
                w.writerow(["{:.3f}".format(r['rate']).encode('utf-8'),
                            str(r['seq']).encode('utf-8') if r['seq'] is not None else b'',
                            r['sent_time'].encode('utf-8'),
                            r['recv_time'].encode('utf-8'),
                            "{:.6f}".format(r['delay_s']).encode('utf-8'),
                            r['send_log'].encode('utf-8'),
                            raw_enc])

    return avg_out, per_packet_out

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="Experiment directory (contains mgen_recv.log and logs/)")
    ap.add_argument("--recv", default=None, help="Receiver log filename (optional)")
    ap.add_argument("--logs", default="logs", help="Sender logs directory (default 'logs')")
    args = ap.parse_args()

    basedir = args.dir
    recv_path = args.recv if args.recv else find_recv_file(basedir)
    if not recv_path:
        print("Receiver log not found in", basedir)
        return
    if not os.path.isabs(recv_path):
        recv_path = os.path.join(basedir, recv_path) if not os.path.isabs(recv_path) else recv_path

    logs_dir = args.logs if os.path.isabs(args.logs) else os.path.join(basedir, args.logs)
    if not os.path.isdir(logs_dir):
        print("Logs directory not found:", logs_dir)
        return

    print("Using recv log:", recv_path)
    print("Using send logs dir:", logs_dir)

    recv_entries = parse_recv_entries(recv_path)
    print("Found RECV entries:", len(recv_entries))
    if not recv_entries:
        print("No RECV entries found. Exiting.")
        return

    start_dt = read_mgen_start_time_from_log(recv_path)
    if start_dt is None:
        start_dt = recv_entries[0]['recv_dt']
        print("No START line found in recv log; using first recv timestamp as start:", start_dt.time())
    else:
        print("MGEN start timestamp from recv log:", start_dt.time())

    intervals = build_intervals_from_sendlogs(logs_dir, start_dt)
    print("Found intervals from send logs:", len(intervals))
    for i, it in enumerate(intervals[:50]):
        print("  Interval {}: start={} end={} rate={} file={}".format(i, it[0].time(), it[1].time(), it[2], it[3]))

    per_rate_delays, per_packet_rows, unknown = map_recv_entries_to_rates(recv_entries, intervals, start_dt)
    print("Mapped packet counts by rate:", {k: len(v) for k, v in per_rate_delays.items()})

    out_avg, out_pp = write_csvs(basedir, per_rate_delays, per_packet_rows)
    print("Wrote:", out_avg, out_pp)

    if unknown:
        print("Warning: {} packets not mapped to any interval (first 5 shown):".format(len(unknown)))
        for e in unknown[:5]:
            print("  recv:", e['recv_dt'].time(), "sent:", e['sent_dt'].time(), "raw:", e['raw'][:120])

if __name__ == "__main__":
    main()
