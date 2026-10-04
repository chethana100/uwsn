# Mirrors AquaSimTrustQVBF::TransmissionProbability exactly (Eqs. 6-10), offline arithmetic only.
import math
def alpha_dB(f):  # Thorp, dB/km, f in kHz (Eq. 7)
    f2=f*f; return 0.11*f2/(1+f2)+44*f2/(4100+f2)+2.75e-4*f2+0.003
def p(d_m, ebn0_dB, f=25.0, k=1.5, m=640, unit=1000.0):
    d=d_m/unit
    if d<=0: return 1.0
    A=d**k*(10**(alpha_dB(f)/10))**(d_m/1000.0)   # absorption always per km; spreading in 'unit'
    snr=10**(ebn0_dB/10)/A
    pe=0.5*(1-math.sqrt(snr/(1+snr)))
    return (1-pe)**m
t=math.tanh(0.25)
print("alpha(25kHz) dB/km = %.4f" % alpha_dB(25))
print("p(1000m,40dB) = %.4f" % p(1000,40))
print("monotone check: p decreasing on 1..1000 m at 40 dB:", all(p(d,40)>=p(d+1,40) for d in range(1,1000)))
print("bound EE >= 0.5*(1-tanh(1/4))*p(1000) = 0.5*%.4f*%.4f = %.4f" % (1-t, p(1000,40), 0.5*(1-t)*p(1000,40)))
def solve(target, d=1000, **kw):
    lo,hi=-40,80
    for _ in range(200):
        mid=(lo+hi)/2
        if p(d,mid,**kw)<target: lo=mid
        else: hi=mid
    return hi
print("freeze-feasibility thresholds at d=1000 m (Eb/N0 below which a freeze becomes POSSIBLE):")
for lab,ss,var in [("SS=0, var=1/4 (worst case)",0,0.25),("SS=0, var=0",0,0.0),("SS=0.5 (no-velocity default), var=0",0.5,0.0)]:
    need_ccq = 2*0.3 - ss          # 0.5*CCQ + 0.5*SS < 0.3  <=> CCQ < 0.6 - SS
    need_p = need_ccq/(1-math.tanh(var))
    print("  %-38s needs p < %.4f  -> Eb/N0 < %.2f dB" % (lab, need_p, solve(need_p)))
print("SS >= 0.6 => EE >= 0.3 for ANY CCQ (no freeze possible regardless of Eb/N0)")
print("p(1000 m) with spreading distance in metres, 40 dB: %.3e  (equivalent shift %.1f dB)" % (p(1000,40,unit=1.0), -30*1.5))
for d in (100,):
    for e in (5,20,40):
        print("EAQTE-scale d=%d m, Eb/N0=%d dB: p=%.4f" % (d,e,p(d,e)))
for e in (10,20,30,35,40,50):
    print("Eb/N0=%2d dB: p(100m)=%.4f p(500m)=%.4f p(1000m)=%.4f" % (e,p(100,e),p(500,e),p(1000,e)))
for k in (1.0,2.0):
    print("k=%.1f: p(1000m,40dB)=%.4f" % (k,p(1000,40,k=k)))
