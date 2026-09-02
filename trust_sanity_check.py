import sys
import re
from collections import defaultdict

TRACE_PATH = "uwsn-paper-baseline.tr"
DELTA = 0.7
INITIAL_TRUST = 0.5


def parse_events(path):
    transmits = []
    receipts = []

    current_event = None
    current_node = None
    current_time = None

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tokens = line.split()
            first = tokens[0]

            if first in ('t', 'r', 'd'):
                current_event = first
                current_node = None
                current_time = None
                if len(tokens) > 1:
                    try:
                        current_time = float(tokens[1])
                    except ValueError:
                        current_time = None
                if len(tokens) > 2:
                    m = re.search(r'/NodeList/(\d+)/', tokens[2])
                    if m:
                        current_node = int(m.group(1))

            m_uid = re.search(r'UniqueID=(\d+)', line)
            m_sender = re.search(r'SenderAddr=0*(\d+)', line)

            if m_uid and current_event == 't' and current_node is not None and current_time is not None:
                uid = int(m_uid.group(1))
                transmits.append((current_node, uid, current_time))
                current_event = None

            elif m_uid and current_event == 'r' and current_node is not None and current_time is not None and m_sender:
                uid = int(m_uid.group(1))
                sender_addr = int(m_sender.group(1))
                sender_node = sender_addr - 1
                receipts.append((sender_node, current_node, uid, current_time))
                current_event = None

    return transmits, receipts


def build_forward_lookup(transmits):
    forward_times = defaultdict(list)
    for node_id, uid, t in transmits:
        forward_times[(node_id, uid)].append(t)
    for key in forward_times:
        forward_times[key].sort()
    return forward_times


def compute_direct_trust(transmits, receipts):
    forward_times = build_forward_lookup(transmits)
    events_per_pair = defaultdict(list)

    for sender_node, receiver_node, uid, recv_time in receipts:
        candidate_times = forward_times.get((receiver_node, uid), [])
        forwarded = any(t > recv_time for t in candidate_times)
        events_per_pair[(sender_node, receiver_node)].append((recv_time, forwarded))

    trust_trajectory = {}
    final_trust = {}

    for pair, events in events_per_pair.items():
        events.sort(key=lambda e: e[0])
        trust = INITIAL_TRUST
        trajectory = []
        for t, success in events:
            observation = 1.0 if success else 0.0
            trust = DELTA * trust + (1 - DELTA) * observation
            trajectory.append((t, trust))
        trust_trajectory[pair] = trajectory
        final_trust[pair] = trust

    return trust_trajectory, final_trust, events_per_pair


def main():
    print(f"--- Computing direct trust from: {TRACE_PATH} ---")
    transmits, receipts = parse_events(TRACE_PATH)
    print(f"Transmit events parsed: {len(transmits)}")
    print(f"Receive events parsed : {len(receipts)}")

    trajectory, final_trust, events_per_pair = compute_direct_trust(transmits, receipts)

    print(f"\nNode pairs with at least one observation: {len(final_trust)}")

    if not final_trust:
        print("No observable neighbor-forwarding pairs found -- check trace format.")
        return

    values = list(final_trust.values())
    avg_trust = sum(values) / len(values)
    min_trust = min(values)
    max_trust = max(values)

    print("\n[ Direct Trust Summary (all node pairs) ]")
    print("---------------------------------")
    print(f"Average final trust : {avg_trust:.4f}")
    print(f"Minimum final trust  : {min_trust:.4f}")
    print(f"Maximum final trust  : {max_trust:.4f}")
    print("---------------------------------")

    print("\n[ Example trust trajectories (first 5 pairs with 3+ observations) ]")
    shown = 0
    for pair, traj in trajectory.items():
        if len(traj) >= 3 and shown < 5:
            i, j = pair
            path_str = " -> ".join(f"{t:.1f}s:{v:.3f}" for t, v in traj[:6])
            print(f"  Node {i} evaluating Node {j} ({len(traj)} obs): {path_str}"
                  + (" ..." if len(traj) > 6 else ""))
            shown += 1

    print("\n[ Sanity checks ]")
    print("---------------------------------")
    bounded = all(0.0 <= v <= 1.0 for v in values)
    print(f"All trust values within [0,1]: {bounded}")
    n_pairs_single_obs = sum(1 for traj in trajectory.values() if len(traj) == 1)
    print(f"Pairs with only 1 observation (trust barely moved from {INITIAL_TRUST}): {n_pairs_single_obs}")
    print("---------------------------------\n")


if __name__ == "__main__":
    main()
