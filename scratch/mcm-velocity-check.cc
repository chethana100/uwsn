/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
//
// mcm-velocity-check.cc -- standalone sanity check for McmMobilityModel.
//
// Run this BEFORE trusting the model in the full 3000s trust+Q simulation.
//
// Usage:
//   ./ns3 run mcm-velocity-check
//
// What to check in the output:
//   - Speeds should mostly land in a plausible range (roughly 0.1-2.0 m/s,
//     capped at MaxSpeed=2.0). If everything is near 0, the stream
//     function amplitude is too weak. If everything is pinned at
//     MaxSpeed, the amplitude is too strong (constantly clamping).
//   - Positions should stay within [0, AREA_X] x [0, AREA_Y] x [0, AREA_Z].
//   - Nearby nodes (pair A: 0&1, pair B: 2&3) should show SIMILAR
//     velocity direction/magnitude at the same timestep -- this is the
//     whole point (correlated drift).

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "mcm-mobility-model.h"

#include <iostream>
#include <vector>
#include <string>
#include <cmath>

using namespace ns3;

const double AREA_X = 3000.0;
const double AREA_Y = 3000.0;
const double AREA_Z = 2500.0;
const double CHECK_DURATION = 60.0;
const double LOG_INTERVAL = 5.0;

std::vector<Ptr<MobilityModel>> g_models;
std::vector<std::string> g_labels;

void
LogState ()
{
  double t = Simulator::Now ().GetSeconds ();
  std::cout << "--- t = " << t << "s ---\n";
  for (size_t i = 0; i < g_models.size (); i++)
    {
      Vector pos = g_models[i]->GetPosition ();
      Vector vel = g_models[i]->GetVelocity ();
      double speed = std::sqrt (vel.x * vel.x + vel.y * vel.y);

      bool inBounds = (pos.x >= 0 && pos.x <= AREA_X &&
                        pos.y >= 0 && pos.y <= AREA_Y &&
                        pos.z >= 0 && pos.z <= AREA_Z);

      std::cout << "  " << g_labels[i]
                << " pos=(" << pos.x << "," << pos.y << "," << pos.z << ")"
                << " vel=(" << vel.x << "," << vel.y << ")"
                << " speed=" << speed << " m/s"
                << (inBounds ? "" : "  *** OUT OF BOUNDS ***")
                << "\n";
    }

  if (t + LOG_INTERVAL <= CHECK_DURATION)
    {
      Simulator::Schedule (Seconds (LOG_INTERVAL), &LogState);
    }
}

int main (int argc, char *argv[])
{
  NodeContainer nodes;
  nodes.Create (6);

  std::vector<Vector> startPositions = {
    Vector (500,  500,  100),
    Vector (520,  510,  100),
    Vector (2500, 2500, 100),
    Vector (2480, 2490, 100),
    Vector (1500, 1500, 100),
    Vector (100,  2900, 100),
  };

  MobilityHelper mobility;
  mobility.SetMobilityModel ("ns3::McmMobilityModel",
      "Bounds", BoxValue (Box (0, AREA_X, 0, AREA_Y, 0, AREA_Z)),
      "TimeStep", TimeValue (Seconds (1.0)));
  mobility.Install (nodes);

  for (uint32_t i = 0; i < nodes.GetN (); i++)
    {
      Ptr<MobilityModel> mob = nodes.Get (i)->GetObject<MobilityModel> ();
      mob->SetPosition (startPositions[i]);
      g_models.push_back (mob);
      g_labels.push_back ("Node" + std::to_string (i));
    }

  std::cout << "=== MCM Mobility Model Velocity Check ===\n";
  std::cout << "Node 0 & 1 are close together (pair A) -- expect similar velocity.\n";
  std::cout << "Node 2 & 3 are close together (pair B) -- expect similar velocity.\n";
  std::cout << "Node 4 (center) & Node 5 (far corner) are isolated references.\n\n";

  Simulator::Schedule (Seconds (0.0), &LogState);
  Simulator::Stop (Seconds (CHECK_DURATION));
  Simulator::Run ();
  Simulator::Destroy ();

  std::cout << "\n=== Check complete ===\n";

  return 0;
}	
