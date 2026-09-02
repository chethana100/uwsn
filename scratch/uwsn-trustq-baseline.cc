/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
//
// Trust+Q arm -- AquaSimTrustQVBF, WITH MOBILITY (Step 3)
//
// [MOBILITY NOTE] Aqua-Sim-NG's own AquaSimMobilityKinematic implements a
// genuine Meandering Current Mobility (MCM) model matching the literature
// (Xu et al.-style stream function, same family EAQTE/QLTM/T-SAPR use), but
// its RestrictLocByBound()/BounceByEdge() has a pass-by-value bug that
// prevents boundary bouncing from ever taking effect (verified against
// aqua-sim-mobility-pattern.cc: coord and dspeed are passed by value, the
// bounced position is computed then discarded, only the recheck bool is
// returned). Rather than patch Aqua-Sim-NG's own unexercised code, we use
// ns-3's standard GaussMarkovMobilityModel as a documented approximation
// of correlated, current-like drift. This should be stated explicitly as
// a limitation in the methods section.
//
// All fixes from the corrected baseline carried forward:
//  [FIX 1] RngSeedManager::SetSeed/SetRun
//  [FIX 2] CommandLine parsing (--run, --tag, --priorityScale)
//  [FIX 3] Extended duration (2900 / 3000)
//  [FIX 4] App-layer Tx counting -> metadata CSV
//  [FIX 5] No NetAnim
//  [FIX 6] Run/tag-specific filenames
//  [TRUST FIX] UpdateSelfTrust only called on genuine wins

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/aqua-sim-ng-module.h"
#include "ns3/applications-module.h"
#include "mcm-mobility-model.h"

#include <vector>
#include <algorithm>
#include <random>
#include <fstream>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("UwsnTrustQBaseline");

const uint32_t NUM_NODES        = 100;
const uint32_t SINK_NODE_INDEX  = 0;
const double   AREA_X           = 3000.0;
const double   AREA_Y           = 3000.0;
const double   AREA_Z           = 2500.0;

const Vector   SINK_POSITION    = Vector (1500.0, 1500.0, 0.0);

const double   TRANS_RANGE      = 1000.0;

const double   TX_POWER         = 10.0;
const double   RX_POWER         = 3.0;
const double   IDLE_POWER       = 0.03;
const double   INITIAL_ENERGY   = 10000.0;

const double   VBF_WIDTH        = 400.0;

const double   TRUST_WEIGHT     = 0.3;
const double   TRUST_DECAY      = 0.7;

const uint32_t NUM_SOURCES      = 10;
const uint32_t PACKET_SIZE      = 80;
const double   PACKET_RATE_PPS  = 0.033;

const double   TRAFFIC_START    = 2.0;
const double   TRAFFIC_STOP     = 2900.0;
const double   SIM_DURATION     = 3000.0;

const uint32_t BASE_SEED        = 12345;
const double   ENERGY_SAMPLE_INTERVAL = 10.0;

const double   MOBILITY_ALPHA        = 0.85;
const double   MOBILITY_MEAN_VEL_MIN = 0.5;
const double   MOBILITY_MEAN_VEL_MAX = 1.5;

std::ofstream g_energyFile;
NetDeviceContainer g_devices;

static uint32_t g_appPacketsSent = 0;

void
AppTxCallback (Ptr<const Packet> packet)
{
  g_appPacketsSent++;
}

void
SampleEnergy ()
{
  double now = Simulator::Now ().GetSeconds ();
  for (uint32_t i = 0; i < g_devices.GetN (); i++)
    {
      Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice> (g_devices.Get (i));
      if (dev && dev->EnergyModel ())
        {
          double energy = dev->EnergyModel ()->GetEnergy ();
          g_energyFile << now << "," << i << "," << energy << "\n";
        }
    }

  if (now + ENERGY_SAMPLE_INTERVAL <= SIM_DURATION)
    {
      Simulator::Schedule (Seconds (ENERGY_SAMPLE_INTERVAL), &SampleEnergy);
    }
}

int main (int argc, char *argv[])
{
  uint32_t runNumber = 1;
  std::string tag = "trustq";
  double priorityScale = -1.0;

  CommandLine cmd;
  cmd.AddValue ("run", "Run number (varies RNG seed and output filenames)", runNumber);
  cmd.AddValue ("tag", "Tag prefix for output filenames", tag);
  cmd.AddValue ("priorityScale", "Override PriorityScale attribute (-1 = use class default)", priorityScale);
  cmd.Parse (argc, argv);

  RngSeedManager::SetSeed (BASE_SEED);
  RngSeedManager::SetRun (runNumber);

  LogComponentEnable ("UwsnTrustQBaseline", LOG_LEVEL_INFO);
  NS_LOG_INFO ("--- Initializing Trust+Q-Learning HH-VBF Test (AquaSimTrustQVBF), run "
               << runNumber << ", tag " << tag << " (with mobility) ---");

  NodeContainer nodes;
  nodes.Create (NUM_NODES);

  MobilityHelper sensorMobility;
  sensorMobility.SetPositionAllocator ("ns3::RandomBoxPositionAllocator",
      "X", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_X) + "]"),
      "Y", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Y) + "]"),
      "Z", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Z) + "]"));

  sensorMobility.SetMobilityModel ("ns3::GaussMarkovMobilityModel",
      "Bounds", BoxValue (Box (0, AREA_X, 0, AREA_Y, 0, AREA_Z)),
      "TimeStep", TimeValue (Seconds (1.0)),
      "Alpha", DoubleValue (MOBILITY_ALPHA),
      "MeanVelocity", StringValue ("ns3::UniformRandomVariable[Min=" + std::to_string (MOBILITY_MEAN_VEL_MIN)
                                    + "|Max=" + std::to_string (MOBILITY_MEAN_VEL_MAX) + "]"),
      "MeanDirection", StringValue ("ns3::UniformRandomVariable[Min=0|Max=6.283185]"),
      "MeanPitch", StringValue ("ns3::ConstantRandomVariable[Constant=0]"),
      "NormalVelocity", StringValue ("ns3::NormalRandomVariable[Mean=0|Variance=0.1]"),
      "NormalDirection", StringValue ("ns3::NormalRandomVariable[Mean=0|Variance=0.1]"),
      "NormalPitch", StringValue ("ns3::NormalRandomVariable[Mean=0|Variance=0.02]"));

  sensorMobility.Install (nodes);

  MobilityHelper sinkMobility;
  sinkMobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  sinkMobility.Install (nodes.Get (SINK_NODE_INDEX));
  Ptr<MobilityModel> sinkMob = nodes.Get (SINK_NODE_INDEX)->GetObject<MobilityModel> ();
  sinkMob->SetPosition (SINK_POSITION);

  AquaSimChannelHelper channelHelper = AquaSimChannelHelper::Default ();
  Ptr<AquaSimChannel> channel = channelHelper.Create ();

  AquaSimHelper asHelper = AquaSimHelper::Default ();
  asHelper.SetChannel (channel);

  asHelper.SetEnergyModel ("ns3::AquaSimEnergyModel",
                            "RxPower", DoubleValue (RX_POWER),
                            "TxPower", DoubleValue (TX_POWER),
                            "IdlePower", DoubleValue (IDLE_POWER),
                            "InitialEnergy", DoubleValue (INITIAL_ENERGY));

  asHelper.SetMac ("ns3::AquaSimBroadcastMac");

  if (priorityScale >= 0.0)
    {
      asHelper.SetRouting ("ns3::AquaSimTrustQVBF",
                            "HopByHop", IntegerValue (1),
                            "Width", DoubleValue (VBF_WIDTH),
                            "TargetPos", Vector3DValue (SINK_POSITION),
                            "TrustWeight", DoubleValue (TRUST_WEIGHT),
                            "TrustDecay", DoubleValue (TRUST_DECAY),
                            "PriorityScale", DoubleValue (priorityScale));
      NS_LOG_INFO ("PriorityScale overridden via CommandLine: " << priorityScale);
    }
  else
    {
      asHelper.SetRouting ("ns3::AquaSimTrustQVBF",
                            "HopByHop", IntegerValue (1),
                            "Width", DoubleValue (VBF_WIDTH),
                            "TargetPos", Vector3DValue (SINK_POSITION),
                            "TrustWeight", DoubleValue (TRUST_WEIGHT),
                            "TrustDecay", DoubleValue (TRUST_DECAY));
      NS_LOG_INFO ("PriorityScale not overridden -- using class compiled default.");
    }

  NetDeviceContainer devices;
  for (uint32_t i = 0; i < nodes.GetN (); i++)
    {
      Ptr<AquaSimNetDevice> newDevice = CreateObject<AquaSimNetDevice> ();
      devices.Add (asHelper.Create (nodes.Get (i), newDevice));
      newDevice->GetPhy ()->SetTransRange (TRANS_RANGE);
    }
  g_devices = devices;

  PacketSocketHelper packetSocket;
  packetSocket.Install (nodes);

  PacketSocketAddress socket;
  socket.SetSingleDevice (devices.Get (SINK_NODE_INDEX)->GetIfIndex ());
  socket.SetPhysicalAddress (devices.Get (SINK_NODE_INDEX)->GetAddress ());
  socket.SetProtocol (1);

  double dataRateBps = PACKET_RATE_PPS * PACKET_SIZE * 8.0;

  OnOffHelper onoff ("ns3::PacketSocketFactory", Address (socket));
  onoff.SetConstantRate (DataRate (uint64_t (dataRateBps)));
  onoff.SetAttribute ("PacketSize", UintegerValue (PACKET_SIZE));

  std::vector<uint32_t> candidateIndices;
  for (uint32_t i = 0; i < nodes.GetN (); ++i)
    {
      if (i != SINK_NODE_INDEX)
        {
          candidateIndices.push_back (i);
        }
    }
  std::mt19937 rng (BASE_SEED + runNumber);
  std::shuffle (candidateIndices.begin (), candidateIndices.end (), rng);

  std::vector<uint32_t> sourceIndices (candidateIndices.begin (),
                                        candidateIndices.begin () + std::min<size_t> (NUM_SOURCES, candidateIndices.size ()));

  NS_LOG_INFO ("Randomly selected source nodes (traffic generators):");
  for (auto idx : sourceIndices)
    {
      NS_LOG_INFO ("  Node " << idx);
    }

  ApplicationContainer apps;
  double staggerStep = 0.1;
  uint32_t counter = 0;
  for (auto idx : sourceIndices)
    {
      ApplicationContainer app = onoff.Install (nodes.Get (idx));
      app.Start (Seconds (TRAFFIC_START + (counter % 20) * staggerStep));
      app.Stop (Seconds (TRAFFIC_STOP));
      apps.Add (app);
      counter++;
    }

  for (uint32_t i = 0; i < apps.GetN (); i++)
    {
      Ptr<OnOffApplication> onOffApp = DynamicCast<OnOffApplication> (apps.Get (i));
      if (onOffApp)
        {
          onOffApp->TraceConnectWithoutContext ("Tx", MakeCallback (&AppTxCallback));
        }
    }

  std::string trFile = tag + "_" + std::to_string (runNumber) + ".tr";
  std::string energyFileName = tag + "_" + std::to_string (runNumber) + "_energy.csv";
  std::string trustFileName = tag + "_" + std::to_string (runNumber) + "_trust.csv";
  std::string metaFileName = tag + "_" + std::to_string (runNumber) + "_meta.csv";

  AsciiTraceHelper ascii;
  Ptr<OutputStreamWrapper> stream = ascii.CreateFileStream (trFile);
  asHelper.EnableAsciiAll (*stream->GetStream ());

  g_energyFile.open (energyFileName);
  g_energyFile << "time,node_id,residual_energy\n";
  Simulator::Schedule (Seconds (0.0), &SampleEnergy);

  NS_LOG_INFO ("Network configured. Trace file '" << trFile << "', energy log '"
               << energyFileName << "' will be generated.");
  NS_LOG_INFO ("Sink fixed at (" << SINK_POSITION.x << ", " << SINK_POSITION.y
               << ", " << SINK_POSITION.z << ")");

  Simulator::Stop (Seconds (SIM_DURATION));
  Simulator::Run ();

  std::ofstream trustFile (trustFileName);
  trustFile << "node_id,self_trust,times_eligible,times_forwarded,is_malicious\n";
  double totalEnergyConsumed = 0.0;
  for (uint32_t i = 0; i < nodes.GetN (); i++)
    {
      Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice> (g_devices.Get (i));
      if (dev)
        {
          if (dev->EnergyModel ())
            {
              double residual = dev->EnergyModel ()->GetEnergy ();
              totalEnergyConsumed += (INITIAL_ENERGY - residual);
            }
          Ptr<AquaSimTrustQVBF> trustRouting = DynamicCast<AquaSimTrustQVBF> (dev->GetRouting ());
          if (trustRouting)
            {
              trustFile << i << "," << trustRouting->GetSelfTrust () << ","
                        << trustRouting->GetTimesEligible () << ","
                        << trustRouting->GetTimesForwarded () << ",0\n";
            }
        }
    }
  trustFile.close ();
  Simulator::Destroy ();

  g_energyFile.close ();

  std::ofstream metaFile (metaFileName);
  metaFile << "app_packets_sent,packet_size_bytes,sim_duration,total_energy_consumed_J\n";
  metaFile << g_appPacketsSent << "," << PACKET_SIZE << "," << SIM_DURATION << ","
           << totalEnergyConsumed << "\n";
  metaFile.close ();

  NS_LOG_INFO ("App packets sent (correct PDR denominator): " << g_appPacketsSent);

  return 0;
}
