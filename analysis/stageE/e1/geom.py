"""Stage E — constants and pure geometry shared by the observer and the evaluation code.
No file I/O and no ground truth (frozen spec rev 2, ../README.md §5–§7)."""
import math

# Public protocol constants (README §5)
R, W, PRIO, TDELAY, V0 = 1000.0, 400.0, 1.5, 1.0, 1500.0
SINK = 1                      # sink address (node 0)
TGT = (1500.0, 1500.0, 0.0)   # routing target (also carried in every header as tgt)
# O1 constants (README §6)
EPS, STALE, WINDOW = 25.0, 60.0, 8.0
# O2 stratum boundaries (README §7)
AGE_EDGES = (20.0, 40.0)      # K3: <=20 s, 20-40 s, 40-60 s

WRAP_T, WRAP = 2147483.648, 4294967.296


def unwrap(v):                # VBHeader d: negative components arrive wrapped as uint32/1000
    return v - WRAP if v > WRAP_T else v


def res6(v):                  # half a unit in the 6th significant digit (ostream default precision)
    return 0.5 * 10 ** (math.floor(math.log10(abs(v))) - 5) if v else 1e-12


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    return math.sqrt(dot(a, a))


def dist(a, b):
    return norm(sub(a, b))


def projection(x, o, tgt):    # perpendicular distance from x to the line o -> tgt
    w, v = sub(tgt, o), sub(x, o)
    cx, cy, cz = v[1] * w[2] - v[2] * w[1], v[2] * w[0] - v[0] * w[2], v[0] * w[1] - v[1] * w[0]
    l = norm(w)
    return 0.0 if l == 0 else math.sqrt(cx * cx + cy * cy + cz * cz) / l


def dcos(x, f, tgt):
    v, w = sub(x, f), sub(tgt, f)
    dd, l = norm(v), norm(w)
    return dd, (0.0 if dd == 0 or l == 0 else dot(v, w) / (dd * l))


def alpha_aquasim(x, o, f, tgt):   # Aqua-Sim-NG CalculateDelay (VBF Def. 1), hop-by-hop pipe origin o
    dd, ct = dcos(x, f, tgt)
    return projection(x, o, tgt) / W + (R - dd * ct) / R


def alpha_prime(x, f, tgt):        # HH-VBF Def. 2
    dd, ct = dcos(x, f, tgt)
    return (R - dd * ct) / R


def hold_paper(x, f, tgt):         # published hold time, used only to rank candidates
    a = max(0.0, alpha_prime(x, f, tgt))
    return math.sqrt(a) * TDELAY + (R - dist(x, f)) / V0


def p_success(d_m, ebn0_db, f_khz=25.0, k=1.5, m_bits=640.0):
    """EAQTE Eqs. 6-10 exactly as AquaSimTrustQVBF::TransmissionProbability (d in km; EbN0 = 10^(dB/10))."""
    d_km = d_m / 1000.0
    if d_km <= 0.0:
        return 1.0
    f2 = f_khz * f_khz
    alpha_db = 0.11 * (f2 / (1.0 + f2)) + 44.0 * (f2 / (4100.0 + f2)) + 2.75e-4 * f2 + 0.003
    a = (d_km ** k) * ((10.0 ** (alpha_db / 10.0)) ** d_km)
    snr = (10.0 ** (ebn0_db / 10.0)) / a
    pe = 0.5 * (1.0 - math.sqrt(snr / (1.0 + snr)))
    return min(1.0, max(0.0, (1.0 - pe) ** m_bits))


def age_bin(age):                  # K3
    return 0 if age <= AGE_EDGES[0] else (1 if age <= AGE_EDGES[1] else 2)


def rank_bin(rank):                # K2
    return 0 if rank == 1 else (1 if rank == 2 else 2)
