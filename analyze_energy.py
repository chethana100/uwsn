import csv
from collections import defaultdict

ENERGY_CSV_PATH = "energy-trace-trustq.csv"
INITIAL_ENERGY = 10000.0   # must match INITIAL_ENERGY in uwsn-phase1-baseline.cc
NUM_NODES = 100             # must match NUM_NODES in uwsn-phase1-baseline.cc
DEATH_THRESHOLD = 0.0       # a node is considered "dead" at or below this energy


def load_energy_trace(path):
    """Returns {node_id: [(time, energy), ...]} sorted by time per node."""
    per_node = defaultdict(list)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row['time'])
            node_id = int(row['node_id'])
            energy = float(row['residual_energy'])
            per_node[node_id].append((t, energy))

    for node_id in per_node:
        per_node[node_id].sort(key=lambda pair: pair[0])

    return per_node


def compute_energy_consumption(per_node):
    """For each node, consumption = InitialEnergy - final recorded residual energy."""
    consumption = {}
    for node_id, samples in per_node.items():
        if not samples:
            continue
        final_energy = samples[-1][1]
        consumption[node_id] = INITIAL_ENERGY - final_energy
    return consumption


def compute_network_lifetime(per_node, threshold=DEATH_THRESHOLD):
    """
    Network lifetime = the earliest timestamp at which ANY node's residual
    energy drops to or below `threshold` (MLAR's "time of death of the
    first node" definition). Returns None if no node ever reaches the
    threshold during the observed simulation window.
    """
    earliest_death_time = None
    dying_node = None

    for node_id, samples in per_node.items():
        for t, energy in samples:
            if energy <= threshold:
                if earliest_death_time is None or t < earliest_death_time:
                    earliest_death_time = t
                    dying_node = node_id
                break  # only need the first crossing for this node

    return earliest_death_time, dying_node


def main():
    per_node = load_energy_trace(ENERGY_CSV_PATH)

    print(f"--- Energy & Lifetime Analysis: {ENERGY_CSV_PATH} ---")
    print(f"Nodes found in energy log: {len(per_node)}")

    consumption = compute_energy_consumption(per_node)
    total_consumed = sum(consumption.values())
    avg_consumed = total_consumed / len(consumption) if consumption else 0.0
    max_consumed_node = max(consumption, key=consumption.get) if consumption else None
    min_consumed_node = min(consumption, key=consumption.get) if consumption else None

    print("\n[ Energy Consumption ]")
    print("---------------------------------")
    print(f"Total energy consumed (all nodes): {total_consumed:.4f} J")
    print(f"Average energy consumed per node : {avg_consumed:.4f} J")
    if max_consumed_node is not None:
        print(f"Highest consumption: Node {max_consumed_node} "
              f"({consumption[max_consumed_node]:.4f} J)")
        print(f"Lowest consumption : Node {min_consumed_node} "
              f"({consumption[min_consumed_node]:.4f} J)")
    print("---------------------------------")

    death_time, dying_node = compute_network_lifetime(per_node)

    print("\n[ Network Lifetime (MLAR definition: time of first node death) ]")
    print("---------------------------------")
    if death_time is not None:
        print(f"First node death   : Node {dying_node}")
        print(f"Time of first death: {death_time:.2f} s")
    else:
        print("No node reached the death threshold during this simulation run.")
        print("(This means the simulation duration may be too short to observe")
        print(" node death at this power/traffic configuration -- consider a")
        print(" longer SIM_DURATION if you need this metric to be non-trivial.)")
    print("---------------------------------\n")


if __name__ == "__main__":
    main()
