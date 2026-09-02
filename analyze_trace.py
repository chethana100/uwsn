#!/usr/bin/env python3
"""
analyze_trace.py  --  CORRECTED trace parser for the UWSN HH-VBF experiments.

WHAT CHANGED, AND WHY
---------------------
[FIX A]  PDR denominator.
         The old parser used len(sent_ids), built from 't' events at ANY node.
         That is "unique packets transmitted", not "packets generated". Any
         packet dropped before its first transmission -- queue overflow, no
         eligible forwarder, energy exhaustion -- never appears, so it vanishes
         from the denominator and INFLATES PDR. Worse, it inflates it more for
         whichever arm drops more packets pre-transmission, which biases the
         very comparison you care about.
         We now read app_packets_sent from the run's _meta.csv, produced by the
         OnOffApplication Tx trace in the .cc file.

[FIX B]  'Packets dropped' is no longer reported as a headline number.
         dropped_ids collected UIDs dropped ANYWHERE, so a packet could appear
         in both dropped_ids and received_ids (dropped by one neighbour,
         delivered via another). The count was not meaningful. It is retained
         only as a diagnostic, clearly labelled.

[FIX C]  Command-line arguments + CSV row output, so 20+ runs can be batched.

[FIX D]  Both PDR definitions are reported side by side, so you can see exactly
         how much the old denominator was inflating your numbers.

USAGE
    python3 analyze_trace.py --trace base_1.tr --meta base_1_meta.csv \
                             --arm baseline --run 1 --out results.csv
"""

import argparse
import csv
import os
import re
import sys

SINK_NODE_INDEX = 0
UID_RE  = re.compile(r'UniqueID=(\d+)')
NODE_RE = re.compile(r'/NodeList/(\d+)/')


def read_meta(path):
    """Read the run metadata written by the .cc file."""
    if not os.path.exists(path):
        sys.stderr.write(
            f"ERROR: metadata file '{path}' not found.\n"
            "The .cc file must write it -- see [FIX 4] in uwsn-phase1-baseline.cc.\n"
            "Without it there is no correct PDR denominator.\n")
        sys.exit(1)
    with open(path, newline='') as f:
        row = next(csv.DictReader(f))
    return row


def parse_trace(path):
    """Single pass over the ASCII trace."""
    transmitted_uids = set()     # 't' anywhere  (old, wrong denominator)
    received_uids    = set()     # 'r' at sink   (numerator -- this was correct)
    dropped_uids     = set()     # diagnostic only
    send_time, recv_time = {}, {}

    event = node = tstamp = None

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                tokens = line.split()

                if tokens[0] in ('t', 'r', 'd'):
                    event, node, tstamp = tokens[0], None, None
                    if len(tokens) > 1:
                        try:
                            tstamp = float(tokens[1])
                        except ValueError:
                            tstamp = None
                    if len(tokens) > 2:
                        m = NODE_RE.search(tokens[2])
                        if m:
                            node = int(m.group(1))

                m_uid = UID_RE.search(line)
                if m_uid and event:
                    uid = int(m_uid.group(1))
                    if event == 't':
                        transmitted_uids.add(uid)
                        if uid not in send_time and tstamp is not None:
                            send_time[uid] = tstamp
                    elif event == 'r' and node == SINK_NODE_INDEX:
                        received_uids.add(uid)
                        if uid not in recv_time and tstamp is not None:
                            recv_time[uid] = tstamp
                    elif event == 'd':
                        dropped_uids.add(uid)
                    event = None
    except FileNotFoundError:
        sys.stderr.write(f"ERROR: trace file '{path}' not found.\n")
        sys.exit(1)

    return transmitted_uids, received_uids, dropped_uids, send_time, recv_time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trace', required=True)
    ap.add_argument('--meta',  required=True)
    ap.add_argument('--arm',   required=True, help='baseline | trustq | ...')
    ap.add_argument('--run',   required=True, type=int)
    ap.add_argument('--out',   default='results.csv')
    args = ap.parse_args()

    meta = read_meta(args.meta)
    app_sent   = int(meta['app_packets_sent'])
    pkt_bytes  = int(meta['packet_size_bytes'])
    sim_dur    = float(meta['sim_duration'])
    energy_J   = float(meta['total_energy_consumed_J'])

    tx, rx, dropped, send_time, recv_time = parse_trace(args.trace)

    delivered = len(rx)

    # [FIX A] correct PDR
    pdr = 100.0 * delivered / app_sent if app_sent else 0.0
    # [FIX D] old (inflated) PDR, for comparison only
    pdr_old = 100.0 * delivered / len(tx) if tx else 0.0

    delays = [recv_time[u] - send_time[u]
              for u in rx
              if u in send_time and u in recv_time and recv_time[u] >= send_time[u]]

    avg_d = sum(delays) / len(delays) if delays else 0.0
    min_d = min(delays) if delays else 0.0
    max_d = max(delays) if delays else 0.0

    throughput = delivered * pkt_bytes * 8 / sim_dur if sim_dur else 0.0

    print(f"\n[{args.arm}  run={args.run}]")
    print("-" * 46)
    print(f"  App packets generated : {app_sent}          <- denominator")
    print(f"  Unique UIDs transmitted: {len(tx)}          (old denominator)")
    print(f"  Delivered to sink      : {delivered}")
    print(f"  PDR (correct)          : {pdr:.2f}%")
    print(f"  PDR (old method)       : {pdr_old:.2f}%   <- inflated by "
          f"{pdr_old - pdr:+.2f} pts")
    print(f"  Delay avg/min/max      : {avg_d:.4f} / {min_d:.4f} / {max_d:.4f} s")
    print(f"  Delay samples          : {len(delays)} of {delivered} delivered")
    print(f"  Throughput             : {throughput:.4f} bps")
    print(f"  Energy consumed        : {energy_J:.1f} J")
    print(f"  [diag] UIDs dropped somewhere: {len(dropped)} "
          f"(NOT a loss count -- see [FIX B])")
    print("-" * 46)

    header = ['arm', 'run', 'app_packets_sent', 'uids_transmitted', 'delivered',
              'pdr', 'pdr_old_method', 'avg_delay_s', 'min_delay_s', 'max_delay_s',
              'throughput_bps', 'energy_consumed_J']
    row = [args.arm, args.run, app_sent, len(tx), delivered,
           round(pdr, 4), round(pdr_old, 4), round(avg_d, 6), round(min_d, 6),
           round(max_d, 6), round(throughput, 4), round(energy_J, 2)]

    need_header = not os.path.exists(args.out) or os.path.getsize(args.out) == 0
    with open(args.out, 'a', newline='') as f:
        w = csv.writer(f)
        if need_header:
            w.writerow(header)
        w.writerow(row)

    print(f"  -> appended to {args.out}\n")


if __name__ == '__main__':
    main()
