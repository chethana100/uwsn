/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
//
// Trust+Q arm  --  AquaSimTrustQVBF
//
// ############################################################################
// #  WARNING: RECONSTRUCTED FILE.                                            #
// #                                                                          #
// #  You never sent me your actual uwsn-trustq.cc, only the routing class.    #
// #  This is your baseline with the SetRouting() call swapped over.           #
// #                                                                          #
// #  BEFORE RUNNING: open your AquaSimTrustQVBF::GetTypeId() and check that   #
// #  the attribute names below match EXACTLY. If an attribute name is wrong,  #
// #  NS-3 aborts at construction with "Invalid attribute set". If you prefer, #
// #  just take your existing uwsn-trustq.cc and copy in the four blocks       #
// #  marked [FIX 1] .. [FIX 4] from uwsn-phase1-baseline.cc -- that is safer. #
// ############################################################################
//

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/aqua-sim-ng-module.h"
#include "ns3/applications-module.h"

#include <vector>
#include <algorithm>
#include <random>
#include <fstream>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("UwsnTrustQ");

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

const uint32_t NUM_SOURCES      = 10;
const uint32_t PACKET_SIZE      = 80;
const double   PACKET_RATE_PPS  = 0.033;

const double   TRAFFIC_START    = 2.0;
const double   TRAFFIC_STOP     = 2900.0;
const double   SIM_DURATION     = 3000.0;

const uint32_t BASE_SEED        = 12345;
const double   ENERGY_SAMPLE_INTERVAL = 10.0;

std::ofstream       g_energyFile;
NetDeviceContainer  g_devices;
uint32_t            g_appPacketsSent = 0;

void
AppTxTrace (Ptr<const Packet> p)
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
          g_energyFile << now << "," << i << ","
                       << dev->EnergyModel ()->GetEnergy () << "\n";
        }
    }
  if (now + ENERGY_SAMPLE_INTERVAL <= SIM_DURATION)
    {
      Simulator::Schedule (Seconds (ENERGY_SAMPLE_INTERVAL), &SampleEnergy);
    }
}

int
main (int argc, char *argv[])
{
  uint32_t runNumber    = 1;
  double   priorityScale = 0.15;
  std::string tag       = "trustq";

  CommandLine cmd (__FILE__);
  cmd.AddValue ("run", "RNG run number", runNumber);
  cmd.AddValue ("priorityScale", "PriorityScale value", priorityScale);
  cmd.AddValue ("tag", "Output filename prefix", tag);
  cmd.Parse (argc, argv);

  RngSeedManager::SetSeed (BASE_SEED);
  RngSeedManager::SetRun (runNumber);

  LogComponentEnable ("UwsnTrustQ", LOG_LEVEL_INFO);
  NS_LOG_INFO ("=== Trust+Q | run=" << runNumber
               << " priorityScale=" << priorityScale << " ===");

  std::string traceName  = tag + "_" + std::to_string (runNumber) + ".tr";
  std::string energyName = tag + "_" + std::to_string (runNumber) + "_energy.csv";
  std::string metaName   = tag + "_" + std::to_string (runNumber) + "_meta.csv";

  NodeContainer nodes;
  nodes.Create (NUM_NODES);

  MobilityHelper sensorMobility;
  sensorMobility.SetPositionAllocator ("ns3::RandomBoxPositionAllocator",
      "X", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_X) + "]"),
      "Y", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Y) + "]"),
      "Z", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Z) + "]"));
  sensorMobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  sensorMobility.Install (nodes);

  nodes.Get (SINK_NODE_INDEX)->GetObject<MobilityModel> ()->SetPosition (SINK_POSITION);

  AquaSimChannelHelper channelHelper = AquaSimChannelHelper::Default ();
  Ptr<AquaSimChannel> channel = channelHelper.Create ();

  AquaSimHelper asHelper = AquaSimHelper::Default ();
  asHelper.SetChannel (channel);

  asHelper.SetEnergyModel ("ns3::AquaSimEnergyModel",
                           "RxPower",       DoubleValue (RX_POWER),
                           "TxPower",       DoubleValue (TX_POWER),
                           "IdlePower",     DoubleValue (IDLE_POWER),
                           "InitialEnergy", DoubleValue (INITIAL_ENERGY));

  asHelper.SetMac ("ns3::AquaSimBroadcastMac");

  // -------- The only substantive difference from the baseline --------------
  // CHECK THESE ATTRIBUTE NAMES against your GetTypeId() before running.
  asHelper.SetRouting ("ns3::AquaSimTrustQVBF",
                       "HopByHop",      IntegerValue (1),
                       "Width",         DoubleValue (VBF_WIDTH),
                       "TargetPos",     Vector3DValue (SINK_POSITION),
                       "PriorityScale", DoubleValue (priorityScale));

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

  std::vector<uint32_t> sourceIndices (
      candidateIndices.begin (),
      candidateIndices.begin () + std::min<size_t> (NUM_SOURCES, candidateIndices.size ()));

  std::string sourceList;
  ApplicationContainer apps;
  double staggerStep = 0.1;
  uint32_t counter = 0;
  for (auto idx : sourceIndices)
    {
      ApplicationContainer app = onoff.Install (nodes.Get (idx));
      app.Start (Seconds (TRAFFIC_START + (counter % 20) * staggerStep));
      app.Stop  (Seconds (TRAFFIC_STOP));
      app.Get (0)->TraceConnectWithoutContext ("Tx", MakeCallback (&AppTxTrace));
      apps.Add (app);
      sourceList += (counter ? " " : "") + std::to_string (idx);
      counter++;
    }

  AsciiTraceHelper ascii;
  Ptr<OutputStreamWrapper> stream = ascii.CreateFileStream (traceName);
  asHelper.EnableAsciiAll (*stream->GetStream ());

  g_energyFile.open (energyName.c_str ());
  g_energyFile << "time,node_id,residual_energy\n";
  Simulator::Schedule (Seconds (0.0), &SampleEnergy);

  Simulator::Stop (Seconds (SIM_DURATION));
  Simulator::Run ();

  double totalConsumed = 0.0;
  for (uint32_t i = 0; i < g_devices.GetN (); i++)
    {
      Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice> (g_devices.Get (i));
      if (dev && dev->EnergyModel ())
        {
          totalConsumed += (INITIAL_ENERGY - dev->EnergyModel ()->GetEnergy ());
        }
    }

  Simulator::Destroy ();
  g_energyFile.close ();

  std::ofstream metaFile (metaName.c_str ());
  metaFile << "run,app_packets_sent,num_sources,traffic_start,traffic_stop,"
              "sim_duration,packet_size_bytes,total_energy_consumed_J,sources\n";
  metaFile << runNumber << "," << g_appPacketsSent << "," << NUM_SOURCES << ","
           << TRAFFIC_START << "," << TRAFFIC_STOP << "," << SIM_DURATION << ","
           << PACKET_SIZE << "," << totalConsumed << ",\"" << sourceList << "\"\n";
  metaFile.close ();

  NS_LOG_INFO ("run=" << runNumber
               << " app_packets_sent=" << g_appPacketsSent
               << " energy_consumed=" << totalConsumed << " J");
  return 0;
}
