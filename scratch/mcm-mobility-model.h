/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef MCM_MOBILITY_MODEL_H
#define MCM_MOBILITY_MODEL_H

//
// McmMobilityModel -- Meandering Current Mobility, per EAQTE Eq.(1)-(5) /
// QLTM Eq.(1)-(5) / Caruso et al. 2008 (the original source both papers cite).
//
// WHY THIS EXISTS
// ----------------
// GaussMarkovMobilityModel (previously used in uwsn-trustq-baseline.cc) gives
// every node an INDEPENDENT random walk -- neighbouring nodes have no reason
// to move in similar directions. The environment-masked attack we are
// building depends entirely on the opposite being true: honest neighbours
// should naturally co-drift (same ocean current), so an attacker deliberately
// moving AGAINST that drift is what triggers the environmental gate. Under
// Gauss-Markov there is no shared "normal" direction to deviate from, so the
// whole mechanism has nothing to act on.
//
// MCM fixes this: velocity at every point in space comes from a shared,
// smoothly-varying current field (a stream function). Two nearby nodes
// naturally get similar velocities because they sample nearly the same point
// in that field. That is exactly the "co-drift" property EAQTE's SS term
// assumes.
//
// ###########################################################################
// #  OPEN MODELLING DECISION -- READ BEFORE TRUSTING RESULTS FROM THIS FILE  #
// ###########################################################################
//
// EAQTE/QLTM state their meander wavelength as "7.5 km" and current speed as
// "~0.3 m/s", but neither paper shows the unit derivation connecting the raw
// stream-function partial derivatives (which come out as a dimensionless
// number divided by a length) to a physical m/s speed. Papers in this
// sub-field appear to use the model as a MOTION GENERATOR without fully
// resolving that unit chain.
//
// We resolve it as follows, and this is a genuine design choice, not a
// verified physical derivation:
//
//   1. Node (x,y) positions (in metres, ns-3 native) are divided by 1000 to
//      enter the stream function in the km-scale the papers describe.
//   2. The stream function's partial derivatives give a DIRECTION only
//      (unit vector) -- this is the part that matters for our research
//      question, because it is what makes neighbouring nodes co-drift.
//   3. The actual SPEED (magnitude, m/s) is a separate tunable parameter,
//      "VelocityScale", independent of the raw derivative magnitude.
//
// This means: neighbouring nodes will point in similar directions (the
// property we need), but the literal speed number is ours to set, not derived
// from the paper. Default VelocityScale is set to 0.3 m/s to match EAQTE's
// stated current speed. EAQTE's own simulation parameter table separately
// states "node velocity 10-50 m/s" for their SIMULATED node speed (distinct
// from the underlying current speed) -- that number is unusually fast for a
// literal ocean current and we do not attempt to justify it physically; if
// you want direct numerical comparability to EAQTE's reported figures rather
// than physical realism, override VelocityScale accordingly via the
// attribute system. Flag this choice explicitly in the methodology section
// of the report; do not present it as a verified reproduction of their model.
//
// ###########################################################################
//

#include "ns3/mobility-model.h"
#include "ns3/vector.h"
#include "ns3/box.h"
#include "ns3/simulator.h"
#include "ns3/log.h"
#include <cmath>
#include <algorithm>

namespace ns3 {

class McmMobilityModel : public MobilityModel
{
public:
  static TypeId
  GetTypeId (void)
  {
    static TypeId tid = TypeId ("ns3::McmMobilityModel")
      .SetParent<MobilityModel> ()
      .SetGroupName ("Mobility")
      .AddConstructor<McmMobilityModel> ()
      .AddAttribute ("Bounds",
                     "Bounding box nodes drift within (reflected at walls).",
                     BoxValue (Box (0, 3000, 0, 3000, 0, 2500)),
                     MakeBoxAccessor (&McmMobilityModel::m_bounds),
                     MakeBoxChecker ())
      .AddAttribute ("TimeStep",
                     "Interval between velocity/position updates.",
                     TimeValue (Seconds (1.0)),
                     MakeTimeAccessor (&McmMobilityModel::m_timeStep),
                     MakeTimeChecker ())
      .AddAttribute ("VelocityScale",
                     "Current speed in m/s. See file header: this is a "
                     "tunable design choice, not a value derived from the "
                     "stream function's raw units.",
                     DoubleValue (0.3),
                     MakeDoubleAccessor (&McmMobilityModel::m_velocityScale),
                     MakeDoubleChecker<double> (0.0))
      .AddAttribute ("A",
                     "Meander amplitude base term (dimensionless, per Caruso et al.).",
                     DoubleValue (1.2),
                     MakeDoubleAccessor (&McmMobilityModel::m_A),
                     MakeDoubleChecker<double> ())
      .AddAttribute ("C",
                     "Phase velocity (km/model-time-unit).",
                     DoubleValue (0.12),
                     MakeDoubleAccessor (&McmMobilityModel::m_c),
                     MakeDoubleChecker<double> ())
      .AddAttribute ("K",
                     "Wavenumber = 2*pi / meander_wavelength_km.",
                     DoubleValue (2.0 * M_PI / 7.5),
                     MakeDoubleAccessor (&McmMobilityModel::m_k),
                     MakeDoubleChecker<double> ())
      .AddAttribute ("Omega",
                     "Meander amplitude oscillation frequency.",
                     DoubleValue (0.4),
                     MakeDoubleAccessor (&McmMobilityModel::m_omega),
                     MakeDoubleChecker<double> ())
      .AddAttribute ("Epsilon",
                     "Meander amplitude oscillation magnitude.",
                     DoubleValue (0.3),
                     MakeDoubleAccessor (&McmMobilityModel::m_epsilon),
                     MakeDoubleChecker<double> ())
      .AddAttribute ("PositionScaleM",
                     "Metres per formula-unit (papers describe distances in "
                     "km; ns-3 positions are in m). Default 1000 = 1 km.",
                     DoubleValue (1000.0),
                     MakeDoubleAccessor (&McmMobilityModel::m_posScale),
                     MakeDoubleChecker<double> (1.0));
    return tid;
  }

  McmMobilityModel ()
    : m_A (1.2), m_c (0.12), m_k (2.0 * M_PI / 7.5), m_omega (0.4),
      m_epsilon (0.3), m_posScale (1000.0), m_velocityScale (0.3)
  {
    // [FIX] Do NOT rely on Object::DoInitialize() being called -- it is not
    // automatically invoked on mobility models by MobilityHelper::Install(),
    // which is why the first version of this file produced velocity=(0,0)
    // forever: UpdateVelocity() was simply never called.
    //
    // ScheduleNow() posts an event for simulation time 0 but does not run it
    // until Simulator::Run() begins processing the event queue. By that
    // point MobilityHelper::Install() has already called SetPosition() with
    // the real allocated coordinates (that happens synchronously during
    // setup, before Run() executes anything), so m_position is correct by
    // the time this fires. This is the same pattern GaussMarkovMobilityModel
    // uses internally, which is why that model worked and this one didn't.
    m_event = Simulator::ScheduleNow (&McmMobilityModel::Update, this);
  }

private:
  virtual void
  DoDispose (void)
  {
    Simulator::Cancel (m_event);
    MobilityModel::DoDispose ();
  }

  virtual Vector
  DoGetPosition (void) const
  {
    return m_position;
  }

  virtual void
  DoSetPosition (const Vector &position)
  {
    m_position = position;
    NotifyCourseChange ();
  }

  virtual Vector
  DoGetVelocity (void) const
  {
    return m_velocity;
  }

  // Stream function psi(x_km, y_km, t_s), per EAQTE Eq.(1).
  double
  Psi (double x_km, double y_km, double t_s) const
  {
    double Bt = m_A + m_epsilon * std::cos (m_omega * t_s);
    double phase = m_k * (x_km - m_c * t_s);
    double numerator = y_km - Bt * std::sin (phase);
    double denom = std::sqrt (1.0 + m_k * m_k * Bt * Bt * std::cos (phase) * std::cos (phase));
    return -std::tanh (numerator / denom);
  }

  // Direction only (unit vector) from the stream function's gradient, via
  // central finite difference. See file header: magnitude is NOT taken from
  // here, only direction. This is what makes neighbouring nodes co-drift.
  Vector
  DriftDirection (double x_m, double y_m, double t_s) const
  {
    const double h = 0.05; // km, finite-difference step
    double x_km = x_m / m_posScale;
    double y_km = y_m / m_posScale;

    double u = -(Psi (x_km, y_km + h, t_s) - Psi (x_km, y_km - h, t_s)) / (2.0 * h);
    double v =  (Psi (x_km + h, y_km, t_s) - Psi (x_km - h, y_km, t_s)) / (2.0 * h);

    double mag = std::sqrt (u * u + v * v);
    if (mag < 1e-9)
      {
        return Vector (0.0, 0.0, 0.0);
      }
    return Vector (u / mag, v / mag, 0.0); // vertical motion neglected, per papers
  }

  void
  UpdateVelocity (void)
  {
    double t = Simulator::Now ().GetSeconds ();
    Vector dir = DriftDirection (m_position.x, m_position.y, t);
    m_velocity = Vector (dir.x * m_velocityScale,
                         dir.y * m_velocityScale,
                         0.0);
  }

  // Reflect off the bounding box, matching GaussMarkovMobilityModel's
  // boundary behaviour so nodes never leave the simulated volume.
  void
  ReflectAtBounds (void)
  {
    if (m_position.x < m_bounds.xMin) { m_position.x = m_bounds.xMin; m_velocity.x = -m_velocity.x; }
    if (m_position.x > m_bounds.xMax) { m_position.x = m_bounds.xMax; m_velocity.x = -m_velocity.x; }
    if (m_position.y < m_bounds.yMin) { m_position.y = m_bounds.yMin; m_velocity.y = -m_velocity.y; }
    if (m_position.y > m_bounds.yMax) { m_position.y = m_bounds.yMax; m_velocity.y = -m_velocity.y; }
    // z left untouched: vertical motion neglected per EAQTE/QLTM assumption.
  }

  void
  Update (void)
  {
    double dt = m_timeStep.GetSeconds ();
    m_position.x += m_velocity.x * dt;
    m_position.y += m_velocity.y * dt;
    ReflectAtBounds ();

    UpdateVelocity ();
    NotifyCourseChange ();

    m_event = Simulator::Schedule (m_timeStep, &McmMobilityModel::Update, this);
  }

  Vector    m_position;
  Vector    m_velocity;
  Box       m_bounds;
  Time      m_timeStep;
  EventId   m_event;

  double m_A;
  double m_c;
  double m_k;
  double m_omega;
  double m_epsilon;
  double m_posScale;
  double m_velocityScale;
};

NS_OBJECT_ENSURE_REGISTERED (McmMobilityModel);

} // namespace ns3

#endif /* MCM_MOBILITY_MODEL_H */
