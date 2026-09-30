/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
//
// Trust+Q arm -- AquaSimTrustQVBF, WITH MOBILITY + NAIVE ATTACKER (Phase 2)
//
// [GROUND TRUTH] times_dropped counter added -- times_eligible/times_forwarded
// only ever increment inside UpdateSelfTrust, which the malicious-drop path
// never calls. Without times_dropped, a successful attacker is indistinguishable
// from a permanently idle node in every other logged field.
//

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
#include <sstream>
#include <cmath>

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
const uint32_t MALICIOUS_SEED_OFFSET = 99999;
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

std::string
JoinIndices (const std::vector<uint32_t> &indices)
{
  std::ostringstream oss;
  for (size_t i = 0; i < indices.size (); i++)
    {
      if (i > 0) oss << " ";
      oss << indices[i];
    }
  return oss.str ();
}

int main (int argc, char *argv[])
{
  uint32_t runNumber = 1;
  std::string tag = "trustq";
  double priorityScale = -1.0;
  double attackerFraction = 0.0;
  double dropProbability = 0.0;
  bool adversarialMotion = false;
  bool pactEnabled = false;

  CommandLine cmd;
  cmd.AddValue ("run", "Run number (varies RNG seeds and output filenames)", runNumber);
  cmd.AddValue ("tag", "Tag prefix for output filenames", tag);
  cmd.AddValue ("priorityScale", "Override PriorityScale attribute (-1 = use class default)", priorityScale);
  cmd.AddValue ("attackerFraction", "Fraction of non-sink nodes marked malicious. Default 0.0.", attackerFraction);
  cmd.AddValue ("dropProbability", "Probability a malicious node drops a won packet. Default 0.0.", dropProbability);
  cmd.AddValue ("adversarialMotion", "[EAQTE Step 3] If true, malicious nodes reverse drift direction to suppress SS_ij. Default false.", adversarialMotion);
  cmd.AddValue ("pactEnabled", "[PACT] If true, use peer-referenced continuous attenuation instead of EAQTE binary freeze. Default false.", pactEnabled);
  cmd.Parse (argc, argv);

  RngSeedManager::SetSeed (BASE_SEED);
  RngSeedManager::SetRun (runNumber);

  LogComponentEnable ("UwsnTrustQBaseline", LOG_LEVEL_INFO);
  NS_LOG_INFO ("--- Initializing Trust+Q-Learning HH-VBF Test (AquaSimTrustQVBF), run "
               << runNumber << ", tag " << tag << " (mobility + attacker) ---");

  NodeContainer nodes;
  nodes.Create (NUM_NODES);

  MobilityHelper sensorMobility;
  sensorMobility.SetPositionAllocator ("ns3::RandomBoxPositionAllocator",
      "X", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_X) + "]"),
      "Y", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Y) + "]"),
      "Z", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=" + std::to_string (AREA_Z) + "]"));

  sensorMobility.SetMobilityModel ("ns3::McmMobilityModel",
      "Bounds", BoxValue (Box (0, AREA_X, 0, AREA_Y, 0, AREA_Z)),
      "TimeStep", TimeValue (Seconds (1.0)));

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
                            "PactEnabled", BooleanValue (pactEnabled),
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
                            "TrustDecay", DoubleValue (TRUST_DECAY),
                            "PactEnabled", BooleanValue (pactEnabled));
      NS_LOG_INFO ("PriorityScale not overridden -- using class compiled default.");
    }

  std::vector<uint32_t> allNonSinkIndices;
  for (uint32_t i = 0; i < NUM_NODES; ++i)
    {
      if (i != SINK_NODE_INDEX)
        {
          allNonSinkIndices.push_back (i);
        }
    }
  std::mt19937 maliciousRng (BASE_SEED + runNumber + MALICIOUS_SEED_OFFSET);
  std::vector<uint32_t> shuffledForMalicious = allNonSinkIndices;
  std::shuffle (shuffledForMalicious.begin (), shuffledForMalicious.end (), maliciousRng);

  uint32_t numMalicious = static_cast<uint32_t> (std::round (attackerFraction * allNonSinkIndices.size ()));
  std::vector<uint32_t> maliciousIndices (shuffledForMalicious.begin (),
                                           shuffledForMalicious.begin () + std::min<size_t> (numMalicious, shuffledForMalicious.size ()));
  std::sort (maliciousIndices.begin (), maliciousIndices.end ());



  NS_LOG_INFO ("Attacker fraction: " << attackerFraction << " (" << maliciousIndices.size () << " malicious nodes), "
               "drop probability: " << dropProbability);
  if (!maliciousIndices.empty ())
    {
      NS_LOG_INFO ("Malicious nodes: " << JoinIndices (maliciousIndices));
    }

  NetDeviceContainer devices;
  for (uint32_t i = 0; i < nodes.GetN (); i++)
    {
      Ptr<AquaSimNetDevice> newDevice = CreateObject<AquaSimNetDevice> ();
      devices.Add (asHelper.Create (nodes.Get (i), newDevice));
      newDevice->GetPhy ()->SetTransRange (TRANS_RANGE);
    }
  g_devices = devices;

  for (uint32_t i = 0; i < devices.GetN (); i++)
    {
      bool isMalicious = std::binary_search (maliciousIndices.begin (), maliciousIndices.end (), i);
      if (!isMalicious)
        {
          continue;
        }

      Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice> (devices.Get (i));
      if (!dev)
        {
          NS_LOG_WARN ("Node " << i << ": could not DynamicCast to AquaSimNetDevice -- malicious flag NOT applied.");
          continue;
        }

      Ptr<AquaSimTrustQVBF> trustRouting = DynamicCast<AquaSimTrustQVBF> (dev->GetRouting ());
      if (!trustRouting)
        {
          NS_LOG_WARN ("Node " << i << ": GetRouting() did not return an AquaSimTrustQVBF -- malicious flag NOT applied.");
          continue;
        }

      trustRouting->SetAttribute ("IsMalicious", BooleanValue (true));
      trustRouting->SetAttribute ("DropProbability", DoubleValue (dropProbability));

      // [EAQTE Step 3] Same malicious node also gets adversarial motion on
      // its mobility model -- a genuinely different object from the routing
      // agent above, reached via the node itself. If MCM isn't in use
      // (e.g. GaussMarkov fallback), this cast returns null and is a no-op:
      // the drop-based attack still runs, just without motion manipulation.
      Ptr<McmMobilityModel> mob = DynamicCast<McmMobilityModel> (dev->GetNode ()->GetObject<MobilityModel> ());
      if (mob)
        {
          mob->SetAttribute ("AdversarialMotion", BooleanValue (adversarialMotion));
        }
      else if (adversarialMotion)
        {
          NS_LOG_WARN ("Node " << i << ": mobility model is not McmMobilityModel -- AdversarialMotion NOT applied.");
        }
    }

  if (!maliciousIndices.empty ())
    {
      uint32_t checkIdx = maliciousIndices[0];
      Ptr<AquaSimNetDevice> checkDev = DynamicCast<AquaSimNetDevice> (devices.Get (checkIdx));
      Ptr<AquaSimTrustQVBF> checkRouting = checkDev ? DynamicCast<AquaSimTrustQVBF> (checkDev->GetRouting ()) : nullptr;
      NS_LOG_INFO ("Malicious assignment verification: node " << checkIdx << " IsMalicious="
                   << (checkRouting ? (checkRouting->IsMalicious () ? "true" : "false") : "NULL_ROUTING"));
    }

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

  std::vector<uint32_t> candidateIndices = allNonSinkIndices;
  std::mt19937 sourceRng (BASE_SEED + runNumber);
  std::shuffle (candidateIndices.begin (), candidateIndices.end (), sourceRng);

  std::vector<uint32_t> sourceIndices (candidateIndices.begin (),
                                        candidateIndices.begin () + std::min<size_t> (NUM_SOURCES, candidateIndices.size ()));
  std::sort (sourceIndices.begin (), sourceIndices.end ());

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
  trustFile << "node_id,self_trust,times_eligible,times_forwarded,times_dropped,is_malicious,avg_observed_trust,num_observers\n";
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
              // [PACT eval] Node i's reputation AS SEEN BY the network: average
              // of what every other node's observed-trust map says about i.
              // Only counts observers that actually hold a non-default opinion
              // (i.e. have genuinely observed i), so untouched 0.5 defaults
              // from nodes that never interacted with i don't dilute the mean.
              AquaSimAddress addrI = AquaSimAddress::ConvertFrom (dev->GetAddress ());
              double obsSum = 0.0;
              uint32_t obsCount = 0;
              for (uint32_t j = 0; j < nodes.GetN (); j++)
                {
                  if (j == i) continue;
                  Ptr<AquaSimNetDevice> devJ = DynamicCast<AquaSimNetDevice> (g_devices.Get (j));
                  if (!devJ) continue;
                  Ptr<AquaSimTrustQVBF> rtJ = DynamicCast<AquaSimTrustQVBF> (devJ->GetRouting ());
                  if (!rtJ) continue;
                  double opinion = rtJ->GetObservedTrust (addrI);
                  if (opinion != 0.5)
                    {
                      obsSum += opinion;
                      obsCount++;
                    }
                }
              double avgObs = (obsCount > 0) ? (obsSum / obsCount) : 0.5;

              trustFile << i << "," << trustRouting->GetSelfTrust () << ","
                        << trustRouting->GetTimesEligible () << ","
                        << trustRouting->GetTimesForwarded () << ","
                        << trustRouting->GetTimesDropped () << ","
                        << (trustRouting->IsMalicious () ? 1 : 0) << ","
                        << avgObs << "," << obsCount << "\n";
            }
        }
    }
  trustFile.close ();

  // Observer trust: for every node in the network, ask what it currently
  // believes about each KNOWN malicious node, via genuine peer observation
  // (not self-report). This is the real test of whether the Sep 18 fix
  // (crediting only the actually-overheard watched node, not "any third
  // party forwarded it") lets observed trust catch what self-trust can't.
  std::string observedFileName = tag + "_" + std::to_string (runNumber) + "_observed.csv";
  std::ofstream observedFile (observedFileName);
  observedFile << "observer_id,watched_node_id,is_malicious,observed_trust\n";
  for (uint32_t obsIdx = 0; obsIdx < nodes.GetN (); obsIdx++)
    {
      Ptr<AquaSimNetDevice> obsDev = DynamicCast<AquaSimNetDevice> (g_devices.Get (obsIdx));
      if (!obsDev) continue;
      Ptr<AquaSimTrustQVBF> obsRouting = DynamicCast<AquaSimTrustQVBF> (obsDev->GetRouting ());
      if (!obsRouting) continue;

      for (uint32_t watchedIdx : maliciousIndices)
        {
          if (watchedIdx == obsIdx) continue;
          Ptr<AquaSimNetDevice> watchedDev = DynamicCast<AquaSimNetDevice> (g_devices.Get (watchedIdx));
          if (!watchedDev) continue;
          AquaSimAddress watchedAddr = AquaSimAddress::ConvertFrom (watchedDev->GetAddress ());
          double obsTrust = obsRouting->GetObservedTrust (watchedAddr);
          observedFile << obsIdx << "," << watchedIdx << ",1," << obsTrust << "\n";
        }
    }
  observedFile.close ();

  Simulator::Destroy ();

  g_energyFile.close ();

  std::ofstream metaFile (metaFileName);
  metaFile << "app_packets_sent,packet_size_bytes,sim_duration,total_energy_consumed_J,"
           << "num_sources,sources,attacker_fraction,drop_probability,num_malicious,malicious_nodes\n";
  metaFile << g_appPacketsSent << "," << PACKET_SIZE << "," << SIM_DURATION << ","
           << totalEnergyConsumed << ","
           << sourceIndices.size () << ",\"" << JoinIndices (sourceIndices) << "\","
           << attackerFraction << "," << dropProbability << ","
           << maliciousIndices.size () << ",\"" << JoinIndices (maliciousIndices) << "\"\n";
  metaFile.close ();

  NS_LOG_INFO ("App packets sent (correct PDR denominator): " << g_appPacketsSent);

  return 0;
}
