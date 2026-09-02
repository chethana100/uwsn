"""
UWSN Trace Visualizer (random-deployment version)
----------------------------------------------------
Reads:
  1. An Aqua-Sim-NG ASCII trace file (.tr) for delivery events
  2. The NetAnim XML file for REAL node positions (since nodes are now
     randomly deployed in 3D, not placed on a grid, we can no longer
     recompute positions mathematically -- we read the actual positions
     ns-3 assigned, as recorded by AnimationInterface)

Produces:
  1. topology.png            - static plot of node positions + delivery paths
  2. packet_animation.gif    - animated plot of deliveries over sim time

Usage:
    python3 visualize_trace.py <trace_file.tr> <netanim_xml_file>

Requires: matplotlib
"""

import sys
import re
import matplotlib.pyplot as plt
import matplotlib.animation as animation

SINK_NODE_INDEX = 0


def parse_positions_from_netanim(xml_path):
    positions = {}
    with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.search(r'<node id="(\d+)" sysId="\d+" locX="([\-\d.]+)" locY="([\-\d.]+)"', line)
            if m:
                node_id = int(m.group(1))
                x = float(m.group(2))
                y = float(m.group(3))
                positions[node_id] = (x, y)
    return positions


def parse_trace(file_path):
    seen_uids = set()
    deliveries = []
    all_node_ids = set()
    current_event = None
    current_node = None
    current_time = None

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                        all_node_ids.add(current_node)

            m_uid = re.search(r'UniqueID=(\d+)', line)
            m_sender = re.search(r'SenderAddr=0*(\d+)', line)

            if m_uid and current_event == 'r' and current_node == SINK_NODE_INDEX:
                uid = int(m_uid.group(1))
                if uid not in seen_uids:
                    seen_uids.add(uid)
                    sender = int(m_sender.group(1)) if m_sender else None
                    if current_time is not None and sender is not None:
                        deliveries.append((current_time, sender, uid))
                current_event = None

    return deliveries, all_node_ids


def plot_static_topology(positions, deliveries, sink_id, out_path="topology.png"):
    fig, ax = plt.subplots(figsize=(9, 9))
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    ax.scatter(xs, ys, c='steelblue', s=40, zorder=3, label='Sensor node')

    if sink_id in positions:
        sx, sy = positions[sink_id]
        ax.scatter([sx], [sy], c='red', s=180, marker='*', zorder=4, label='Sink (node 0, fixed)')
    else:
        sx, sy = 0, 0
        print("WARNING: sink position not found in NetAnim XML.")

    for node_id, (x, y) in positions.items():
        ax.annotate(str(node_id), (x, y), textcoords="offset points",
                    xytext=(4, 4), fontsize=6, color='gray')

    for (_, sender, _) in deliveries:
        if sender in positions and sink_id in positions:
            sx2, sy2 = positions[sender]
            ax.plot([sx2, sx], [sy2, sy], color='green', alpha=0.4, linewidth=1, zorder=2)

    ax.set_title(f"UWSN Topology (random 3D deployment) — {len(positions)} nodes, "
                 f"{len(deliveries)} unique deliveries shown in green")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.legend(loc='upper right')
    ax.set_aspect('equal')
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Saved static topology plot -> {out_path}")
    plt.close(fig)


def animate_deliveries(positions, deliveries, sink_id, out_path="packet_animation.gif"):
    if not deliveries:
        print("No successful deliveries found — animation will be empty.")
        return
    if sink_id not in positions:
        print("Sink position not found — cannot animate.")
        return

    deliveries.sort(key=lambda d: d[0])
    t_min = deliveries[0][0]
    t_max = deliveries[-1][0]

    fig, ax = plt.subplots(figsize=(9, 9))
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    ax.scatter(xs, ys, c='lightgray', s=30, zorder=2)
    sx, sy = positions[sink_id]
    ax.scatter([sx], [sy], c='red', s=180, marker='*', zorder=4, label='Sink')
    pad = 200
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect('equal')
    ax.set_title("Packet deliveries over time")
    time_text = ax.text(0.02, 0.98, "", transform=ax.transAxes, va='top')

    lines = []

    def update(frame_time):
        for ln in lines:
            ln.remove()
        lines.clear()

        window = 2.0
        for (t, sender, _uid) in deliveries:
            if frame_time - window <= t <= frame_time and sender in positions:
                sx2, sy2 = positions[sender]
                ln, = ax.plot([sx2, sx], [sy2, sy], color='green', linewidth=1.5, alpha=0.8)
                lines.append(ln)

        time_text.set_text(f"t = {frame_time:.1f}s")
        return lines + [time_text]

    frame_times = [t_min + i * 0.5 for i in range(int((t_max - t_min) / 0.5) + 2)]
    ani = animation.FuncAnimation(fig, update, frames=frame_times, interval=200, blit=False)

    ani.save(out_path, writer='pillow', fps=5)
    print(f"Saved packet delivery animation -> {out_path}")
    plt.close(fig)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 visualize_trace.py <trace_file.tr> <netanim_xml_file>")
        sys.exit(1)

    trace_path = sys.argv[1]
    xml_path = sys.argv[2]

    positions = parse_positions_from_netanim(xml_path)
    deliveries, node_ids = parse_trace(trace_path)

    print(f"Nodes found in NetAnim XML : {len(positions)}")
    print(f"Nodes seen in trace file   : {len(node_ids)}")
    print(f"Unique successful deliveries to sink : {len(deliveries)}")

    plot_static_topology(positions, deliveries, SINK_NODE_INDEX)
    animate_deliveries(positions, deliveries, SINK_NODE_INDEX)


if __name__ == "__main__":
    main()
