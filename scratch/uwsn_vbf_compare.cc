/*
 * uwsn_vbf_compare.cc  (v2 — fixed sink delivery)
 *
 * VBF / HH-VBF baseline for UWSNs, parameterised to match Table 2 of:
 *   Y. Sun, M. Zheng, X. Han, S. Li, J. Yin,
 *   "Adaptive clustering routing protocol for underwater sensor networks",
 *   Ad Hoc Networks 136 (2022) 102953.
 *
 * ---------------------------------------------------------------------
 * WHAT WAS WRONG AND WHAT CHANGED (v1 -> v2)
 * ---------------------------------------------------------------------
 * v1 used a PacketSocket bound on the sink node and expected
 * AquaSimRouting::SendUp() to deliver arriving packets to it. It never
 * did: SendUp() in this Aqua-Sim NG build is an unfinished stub -- it
 * logs, increments a counter, and fires the "RoutingRx" ns-3 trace
 * source (m_routingRxCbTrace), but never calls anything that reaches
 * the node's socket layer. Every earlier "0% PDR" result, at every
 * width and every protocol number, traces back to this one stub -- it
 * was never a routing/geometry/protocol-number problem.
 *
 * v2 removes the sink-side PacketSocket entirely and instead connects
 * directly to the "RoutingRx" trace source on the sink's AquaSimRouting
 * object. That trace fires with the exact packet SendUp() was handed,
 * which is precisely the delivery event we want to measure.
 *
 * The SOURCE side is unaffected by this bug and is left as plain
 * PacketSockets, which is still a valid way to inject packets into the
 * network -- only reception needed to change.
 *
 * Table 2 values used as defaults:
 *   100 sensor nodes + 1 sink        area 3 km x 3 km x 2.5 km
 *   transmission range 1 km          10 source nodes
 *   initial energy 30 000 J          Tx 10 W / Rx 3 W / idle 30 mW
 *   packet size 80 bytes             rate 0.0033 - 0.033 packets/s
 *   simulation time 1000 - 10 000 s  node mobility, max 1 m/s
 *   sink fixed at the surface, infinite energy
 *
 * Paper's VBF baselines are PLAIN VBF with 600 m and 1000 m pipes:
 *   --hopByHop=0 --width=600   and   --hopByHop=0 --width=1000
 * Your HH-VBF is --hopByHop=1. Run all three for a like-for-like comparison.
 *
 * Build: copy to <ns-3>/scratch/ and run ./ns3 run uwsn_vbf_compare
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/aqua-sim-ng-module.h"
#include "ns3/applications-module.h"

#include <vector>
#include <set>
#include <algorithm>
#include <random>
#include <fstream>
#include <iomanip>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("UwsnVbfCompare");

// ---------------------------------------------------------------------------
// Fixed topology constants from Table 2
// ---------------------------------------------------------------------------
static const uint32_t NUM_NODES       = 100;
static const uint32_t SINK_INDEX      = 0;
static const double   AREA_X          = 3000.0;
static const double   AREA_Y          = 3000.0;
static const double   AREA_Z          = 2500.0;
static const Vector   SINK_POSITION   = Vector (1500.0, 1500.0, 0.0);
static const double   TRANS_RANGE     = 1000.0;

static const double   TX_POWER        = 10.0;   // W
static const double   RX_POWER        = 3.0;    // W
static const double   IDLE_POWER      = 0.03;   // W  (30 mW)
static const double   INITIAL_ENERGY  = 30000.0;// J  (paper: 30 000 J)
static const double   SINK_ENERGY     = 1e12;   // stand-in for "infinite"

static const uint32_t NUM_SOURCES     = 10;
static const uint32_t PACKET_SIZE     = 80;     // bytes
static const double   MAX_SPEED       = 1.0;    // m/s

// ---------------------------------------------------------------------------
// Per-packet tag: sequence number (to detect VBF's duplicate deliveries) and
// generation time (for end-to-end latency). A BYTE tag is used so it survives
// copies and reassembly through the Aqua-Sim stack.
// ---------------------------------------------------------------------------
class UwsnTag : public Tag
{
public:
  static TypeId GetTypeId ()
  {
    static TypeId tid = TypeId ("ns3::UwsnTag")
      .SetParent<Tag> ()
      .AddConstructor<UwsnTag> ();
    return tid;
  }
  TypeId GetInstanceTypeId () const override { return GetTypeId (); }
  uint32_t GetSerializedSize () const override { return 4 + 8; }
  void Serialize (TagBuffer i) const override
  {
    i.WriteU32 (m_seq);
    i.WriteDouble (m_time);
  }
  void Deserialize (TagBuffer i) override
  {
    m_seq  = i.ReadU32 ();
    m_time = i.ReadDouble ();
  }
  void Print (std::ostream &os) const override
  {
    os << "seq=" << m_seq << " t=" << m_time;
  }

  void     SetSeq (uint32_t s) { m_seq = s; }
  uint32_t GetSeq () const     { return m_seq; }
  void     SetTime (double t)  { m_time = t; }
  double   GetTime () const    { return m_time; }

private:
  uint32_t m_seq  = 0;
  double   m_time = 0.0;
};

// ---------------------------------------------------------------------------
// Global measurement state
// ---------------------------------------------------------------------------
static std::vector<Ptr<Socket> > g_srcSockets;
static NetDeviceContainer        g_devices;

static uint32_t          g_seqCounter    = 0;   // packets generated
static uint32_t          g_rxRaw         = 0;   // every RoutingRx firing, duplicates included
static std::set<uint32_t> g_rxUnique;           // distinct sequence numbers
static double            g_latencySum    = 0.0;
static uint32_t          g_latencyCount  = 0;
static double            g_firstDeath    = -1.0;// s, -1 = no node died

static std::ofstream     g_energyFile;
static double            g_energyInterval = 10.0;
static double            g_simDuration    = 1000.0;

// ---------------------------------------------------------------------------
// Source: one packet every `interval` seconds. Written by hand rather than
// with OnOffHelper because OnOff goes through DataRate, which is an integer
// number of bits/s -- at 0.0033 packets/s that truncates to 2 bps and silently
// changes the offered load you think you configured.
// ---------------------------------------------------------------------------
void
SendPacket (uint32_t sockIndex, double interval, double stopTime)
{
  if (Simulator::Now ().GetSeconds () > stopTime)
    {
      return;
    }

  Ptr<Packet> p = Create<Packet> (PACKET_SIZE);

  UwsnTag tag;
  tag.SetSeq (g_seqCounter++);
  tag.SetTime (Simulator::Now ().GetSeconds ());
  p->AddByteTag (tag);

  g_srcSockets[sockIndex]->Send (p);

  Simulator::Schedule (Seconds (interval), &SendPacket,
                       sockIndex, interval, stopTime);
}

// ---------------------------------------------------------------------------
// Sink delivery callback -- connected to the sink's "RoutingRx" trace
// source (AquaSimRouting::m_routingRxCbTrace), NOT a socket. This fires
// with exactly the packet AquaSimRouting::SendUp() was handed, which is
// the real delivery event in this Aqua-Sim NG build (SendUp itself never
// forwards the packet any further up the stack).
//
// VBF can flood inside the pipe, so the same packet may trigger this more
// than once. PDR must be computed on UNIQUE sequence numbers or it will
// be inflated.
// ---------------------------------------------------------------------------
void
SinkReceive (Ptr<const Packet> packet)
{
  // Connected to the "PacketReceived" trace source, which is backed by
  // m_routingRxCbTrace -- the TracedCallback<Ptr<const Packet>> that
  // AquaSimRouting::SendUp() actually fires when it hands a packet to
  // "the upper layer". This is the real delivery event.
  if (!packet)
    {
      return;
    }

  g_rxRaw++;

  UwsnTag tag;
  if (packet->FindFirstMatchingByteTag (tag))
    {
      if (g_rxUnique.insert (tag.GetSeq ()).second)
        {
          g_latencySum += (Simulator::Now ().GetSeconds () - tag.GetTime ());
          g_latencyCount++;
        }
    }
}

// ---------------------------------------------------------------------------
// Periodic energy sampling. Also detects the first sensor-node death, which is
// the paper's definition of network lifetime.
// ---------------------------------------------------------------------------
void
SampleEnergy ()
{
  double now = Simulator::Now ().GetSeconds ();

  for (uint32_t i = 0; i < g_devices.GetN (); i++)
    {
      Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice> (g_devices.Get (i));
      if (!dev || !dev->EnergyModel ())
        {
          continue;
        }

      double e = dev->EnergyModel ()->GetEnergy ();
      g_energyFile << now << "," << i << "," << e << "\n";

      if (i != SINK_INDEX && e <= 0.0 && g_firstDeath < 0.0)
        {
          g_firstDeath = now;
          NS_LOG_INFO ("First node death: node " << i << " at t=" << now << " s");
        }
    }

  if (now + g_energyInterval <= g_simDuration)
    {
      Simulator::Schedule (Seconds (g_energyInterval), &SampleEnergy);
    }
}

// ---------------------------------------------------------------------------
int
main (int argc, char *argv[])
{
  // --- tunables ---
  double   width      = 1000.0;  // VBF pipe radius. Paper uses 600 and 1000.
  uint32_t hopByHop   = 1;       // 1 = HH-VBF (yours), 0 = plain VBF (paper's)
  double   rate       = 1.0 / 30.0;   // packets/s per source. Paper sweeps
                                      // 1/300, 1/120, 1/60, 1/30.
  double   simTime    = 1000.0;  // paper sweeps 1000 .. 10000 s
  bool     mobility   = true;    // paper: random motion, max 1 m/s
  uint32_t run        = 1;       // RNG run number, for repeated trials
  std::string label   = "";      // row label in the CSV; auto if empty
  std::string csvPath = "vbf-results.csv";
  bool        traces  = false;   // ASCII + NetAnim traces (large files)

  CommandLine cmd;
  cmd.AddValue ("width",     "VBF pipe radius in metres (600 or 1000)", width);
  cmd.AddValue ("hopByHop",  "1 = HH-VBF, 0 = plain VBF",               hopByHop);
  cmd.AddValue ("rate",      "Packets per second per source node",      rate);
  cmd.AddValue ("simTime",   "Simulation duration in seconds",          simTime);
  cmd.AddValue ("mobility",  "Enable 1 m/s random node motion",         mobility);
  cmd.AddValue ("run",       "ns-3 RNG run number",                     run);
  cmd.AddValue ("label",     "Label for the CSV row",                   label);
  cmd.AddValue ("csv",       "Results CSV path",                        csvPath);
  cmd.AddValue ("traces",    "Write ASCII and NetAnim traces",          traces);
  cmd.Parse (argc, argv);

  g_simDuration = simTime;

  if (label.empty ())
    {
      label = (hopByHop ? "HH-VBF" : "VBF") + std::to_string ((int) width);
    }

  RngSeedManager::SetSeed (42);
  RngSeedManager::SetRun (run);

  LogComponentEnable ("UwsnVbfCompare", LOG_LEVEL_INFO);
  NS_LOG_INFO ("--- " << label << ", rate=" << rate << " pkt/s, simTime="
               << simTime << " s, mobility=" << (mobility ? "on" : "off") << " ---");

  // -------------------------------------------------------------------------
  // Nodes and mobility
  // -------------------------------------------------------------------------
  NodeContainer nodes;
  nodes.Create (NUM_NODES);

  NodeContainer sinkNode;
  NodeContainer sensorNodes;
  for (uint32_t i = 0; i < NUM_NODES; ++i)
    {
      if (i == SINK_INDEX) { sinkNode.Add (nodes.Get (i)); }
      else                 { sensorNodes.Add (nodes.Get (i)); }
    }

  Ptr<ListPositionAllocator> sinkAlloc = CreateObject<ListPositionAllocator> ();
  sinkAlloc->Add (SINK_POSITION);
  MobilityHelper sinkMob;
  sinkMob.SetPositionAllocator (sinkAlloc);
  sinkMob.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  sinkMob.Install (sinkNode);

  MobilityHelper sensorMob;
  sensorMob.SetPositionAllocator ("ns3::RandomBoxPositionAllocator",
      "X", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_X) + "]"),
      "Y", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Y) + "]"),
      "Z", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Z) + "]"));

  if (mobility)
    {
      // Gauss-Markov is used because it is one of the few ns-3 models that
      // moves nodes in 3D. Mean velocity is capped at MAX_SPEED to match the
      // paper's 1 m/s. This is NOT the paper's own mobility model -- they do
      // not name one -- so treat it as a reasonable stand-in, not a match.
      sensorMob.SetMobilityModel ("ns3::GaussMarkovMobilityModel",
          "Bounds", BoxValue (Box (0, AREA_X, 0, AREA_Y, 0, AREA_Z)),
          "TimeStep", TimeValue (Seconds (10.0)),
          "Alpha", DoubleValue (0.85),
          "MeanVelocity", StringValue (
              "ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (MAX_SPEED) + "]"),
          "MeanDirection", StringValue (
              "ns3::UniformRandomVariable[Min=0.0|Max=6.283185307]"),
          "MeanPitch", StringValue (
              "ns3::UniformRandomVariable[Min=-0.05|Max=0.05]"),
          "NormalVelocity", StringValue (
              "ns3::NormalRandomVariable[Mean=0.0|Variance=0.0|Bound=0.0]"),
          "NormalDirection", StringValue (
              "ns3::NormalRandomVariable[Mean=0.0|Variance=0.2|Bound=0.4]"),
          "NormalPitch", StringValue (
              "ns3::NormalRandomVariable[Mean=0.0|Variance=0.02|Bound=0.04]"));
    }
  else
    {
      sensorMob.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    }
  sensorMob.Install (sensorNodes);

  // -------------------------------------------------------------------------
  // Aqua-Sim stack
  // -------------------------------------------------------------------------
  AquaSimChannelHelper channelHelper = AquaSimChannelHelper::Default ();
  Ptr<AquaSimChannel> channel = channelHelper.Create ();

  AquaSimHelper asHelper = AquaSimHelper::Default ();
  asHelper.SetChannel (channel);
  asHelper.SetMac ("ns3::AquaSimBroadcastMac");
  asHelper.SetRouting ("ns3::AquaSimVBF",
                       "HopByHop",  IntegerValue (hopByHop),
                       "Width",     DoubleValue (width),
                       "TargetPos", Vector3DValue (SINK_POSITION));

  NetDeviceContainer devices;

  for (uint32_t i = 0; i < nodes.GetN (); i++)
    {
      asHelper.SetEnergyModel ("ns3::AquaSimEnergyModel",
                               "RxPower",       DoubleValue (RX_POWER),
                               "TxPower",       DoubleValue (TX_POWER),
                               "IdlePower",     DoubleValue (IDLE_POWER),
                               "InitialEnergy", DoubleValue (
                                   i == SINK_INDEX ? SINK_ENERGY : INITIAL_ENERGY));

      Ptr<AquaSimNetDevice> dev = CreateObject<AquaSimNetDevice> ();
      devices.Add (asHelper.Create (nodes.Get (i), dev));
      dev->GetPhy ()->SetTransRange (TRANS_RANGE);
    }
  g_devices = devices;

  // -------------------------------------------------------------------------
  // SINK: connect directly to the RoutingRx trace source (see header comment)
  // -------------------------------------------------------------------------
  Ptr<AquaSimNetDevice> sinkDev = DynamicCast<AquaSimNetDevice> (devices.Get (SINK_INDEX));
  Ptr<AquaSimRouting> sinkRouting = sinkDev->GetRouting ();
  bool traceOk = sinkRouting->TraceConnectWithoutContext ("PacketReceived", MakeCallback (&SinkReceive));
  NS_ABORT_MSG_IF (!traceOk,
      "Could not connect to 'RoutingRx' trace source -- check the exact name "
      "with: grep -n 'AddTraceSource' aqua-sim-routing.cc");

  // -------------------------------------------------------------------------
  // SOURCES: plain packet sockets. This side was never broken -- SendUp()
  // is only in the receive path, so packet generation/injection works as
  // it always did.
  // -------------------------------------------------------------------------
  PacketSocketHelper packetSocket;
  packetSocket.Install (nodes);

  PacketSocketAddress sinkAddr;
  sinkAddr.SetAllDevices ();
  sinkAddr.SetPhysicalAddress (devices.Get (SINK_INDEX)->GetAddress ());
  sinkAddr.SetProtocol (0);

  TypeId psTid = TypeId::LookupByName ("ns3::PacketSocketFactory");

  std::vector<uint32_t> candidates;
  for (uint32_t i = 0; i < NUM_NODES; ++i)
    {
      if (i != SINK_INDEX) { candidates.push_back (i); }
    }
  std::mt19937 rng (42 + run);
  std::shuffle (candidates.begin (), candidates.end (), rng);
  std::vector<uint32_t> sources (candidates.begin (),
                                 candidates.begin () + NUM_SOURCES);

  const double trafficStart = 2.0;
  const double trafficStop  = simTime - 2.0;
  const double stagger      = 0.1;

  NS_LOG_INFO ("Source nodes:");
  for (uint32_t k = 0; k < sources.size (); ++k)
    {
      Ptr<Socket> s = Socket::CreateSocket (nodes.Get (sources[k]), psTid);
      s->Bind ();
      s->Connect (sinkAddr);
      g_srcSockets.push_back (s);

      double start = trafficStart + k * stagger;
      Simulator::Schedule (Seconds (start), &SendPacket,
                           k, 1.0 / rate, trafficStop);
      NS_LOG_INFO ("  node " << sources[k] << " starts at " << start << " s");
    }

  // -------------------------------------------------------------------------
  // Instrumentation
  // -------------------------------------------------------------------------
  g_energyFile.open ("energy-" + label + ".csv");
  g_energyFile << "time,node_id,residual_energy\n";
  Simulator::Schedule (Seconds (0.0), &SampleEnergy);

  Ptr<OutputStreamWrapper> stream;
  if (traces)
    {
      AsciiTraceHelper ascii;
      stream = ascii.CreateFileStream (label + ".tr");
      asHelper.EnableAsciiAll (*stream->GetStream ());
    }

  // -------------------------------------------------------------------------
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  // -------------------------------------------------------------------------
  // Metrics
  // -------------------------------------------------------------------------
  uint32_t sent      = g_seqCounter;
  uint32_t received  = g_rxUnique.size ();
  double   pdr       = (sent > 0) ? (100.0 * received / sent) : 0.0;
  double   avgLat    = (g_latencyCount > 0) ? (g_latencySum / g_latencyCount) : 0.0;
  double   thrBps    = (received * PACKET_SIZE * 8.0) / simTime;
  double   dupRatio  = (received > 0) ? (double (g_rxRaw) / received) : 0.0;

  double residual = 0.0;
  uint32_t alive  = 0;
  for (uint32_t i = 0; i < g_devices.GetN (); i++)
    {
      if (i == SINK_INDEX) { continue; }
      Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice> (g_devices.Get (i));
      if (dev && dev->EnergyModel ())
        {
          double e = dev->EnergyModel ()->GetEnergy ();
          residual += e;
          if (e > 0.0) { alive++; }
        }
    }
  double totalEnergy = (NUM_NODES - 1) * INITIAL_ENERGY - residual;

  std::cout << std::fixed << std::setprecision (4);
  std::cout << "\n========================================\n"
            << "  " << label << "\n"
            << "========================================\n"
            << "Rate (pkt/s/src)  : " << rate            << "\n"
            << "Sim time (s)      : " << simTime         << "\n"
            << "Mobility          : " << (mobility ? "on (1 m/s)" : "off") << "\n"
            << "----------------------------------------\n"
            << "Packets sent      : " << sent            << "\n"
            << "Unique received   : " << received        << "\n"
            << "Raw RoutingRx     : " << g_rxRaw
            << "  (" << dupRatio << " copies per packet)\n"
            << "PDR (%)           : " << pdr             << "\n"
            << "Avg latency (s)   : " << avgLat          << "\n"
            << "Throughput (bps)  : " << thrBps          << "\n"
            << "Energy used (J)   : " << totalEnergy     << "\n"
            << "Nodes alive       : " << alive << " / " << (NUM_NODES - 1) << "\n"
            << "First death (s)   : "
            << (g_firstDeath < 0 ? std::string ("none") : std::to_string (g_firstDeath))
            << "\n========================================\n";

  bool newFile = !std::ifstream (csvPath).good ();
  std::ofstream csv (csvPath, std::ios::app);
  if (newFile)
    {
      csv << "label,hopByHop,width,rate,simTime,mobility,run,"
             "sent,received,pdr,latency_s,throughput_bps,energy_J,"
             "alive,first_death_s\n";
    }
  csv << label << "," << hopByHop << "," << width << "," << rate << ","
      << simTime << "," << mobility << "," << run << ","
      << sent << "," << received << "," << pdr << "," << avgLat << ","
      << thrBps << "," << totalEnergy << "," << alive << ","
      << g_firstDeath << "\n";
  csv.close ();

  Simulator::Destroy ();
  g_energyFile.close ();
  return 0;
}
