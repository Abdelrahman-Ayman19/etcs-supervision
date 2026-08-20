import matplotlib
matplotlib.use("Agg")  # writes image files without opening a window
import matplotlib.pyplot as plt
import numpy as np
import argparse
import sys

from etcs_supervision import (
    SupervisionConfig, emergency_brake_curve, permitted_speed,
    warning_speed, find_violations, simulate_run,
)

KMH = 3.6

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="fahrtauswertung")
    p.add_argument("--brake-at", type=float, default=1250.0,
                    help="Bremsbeginn der simulierten Fahrt in m") # brake-at becomes brake_at
    p.add_argument("--eoa", type=float, default=2000.0,
                    help="Ende der Fahrterlaubnis in m")
    p.add_argument("--decel", type=float, default=0.7, help="Bremsverzoegerung in m/s^2")
    p.add_argument("--out", default="fahrtauswertung.png", help="Dateiname vom PNG")
    return p.parse_args(argv)


def main(argv=None) -> int:

    args = parse_args(argv)

    cfg = SupervisionConfig(eoa_m=args.eoa, decel_ms2=args.decel)
    _, distance, speed = simulate_run(cfg, brake_at_m=args.brake_at)


    ## define the plot and size
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios":[3, 1]}) # 2 rows, 1 col   
        # sharex: both panels use same x

    v_emg = emergency_brake_curve(distance, cfg)
    v_perm = permitted_speed(distance, cfg)
    v_warn = warning_speed(distance, cfg)
    violations = find_violations(distance, speed, v_perm)

    ##### REPORT #####

    print("=" * 72)
    print(f"EOA               : {cfg.eoa_m:.0f} m")
    print(f"Hoechstgeschw.    : {speed.max() * KMH:.1f} km/h")
    print(f"Halt bei          : {distance[-1]:.1f} m ({cfg.eoa_m - distance[-1]:+.1f} m zum EOA)")
    print("=" * 72)
    if violations:
        print(f"[FAIL] Zulaessige Geschwindigkeit ueberschritten: {len(violations)} mal")
        for v in violations:
            print(f"       {v.start_m:7.1f} m bis {v.end_m:7.1f} m | "
                  f"max. {v.max_excess_ms * KMH:5.1f} km/h bei {v.at_m:.1f} m")
    else:
        print("[ OK ] Keine Verletzung")
    print("ERGEBNIS: " + ("FAIL" if violations else "PASS"))

    ##### PLOT #####

    ax1.plot(distance, v_emg * KMH, color="#c0392b", lw=1.8, label= "Bremskurve")
    ax1.plot(distance, v_perm * KMH, color="#e67e22", lw=1.8, label="zulaessige Geschwindigkeit")
    ax1.plot(distance, v_warn * KMH, color="#288500", lw=1.5, ls="--", label="Vorwarnung")
    ax1.plot(distance, speed * KMH,  color="#000000", lw=2.2, label="gefahrene Geschwindigkeit")

    ax1.set_ylabel("geschwindigkeit [km/h]", fontsize=12) # names y-axis
    ax1.grid(alpha=0.3)

    ax1.fill_between(distance, v_perm * KMH, speed * KMH,
                    where= speed > v_perm, alpha=0.4, color="#c0392b",
                    label="Überschreitung") # shade the over-speed part
    ax1.axvline(cfg.eoa_m, color="black", lw=2.5, ls="--")
    ax1.annotate("EOA", xy=(cfg.eoa_m, ax1.get_ylim()[1] * 0.55),
                xytext=(-40, 0), textcoords="offset points",
                fontsize=10, fontweight="bold")

    for i, v in enumerate(violations): # where is the max-excess and how much was the diff between speed and v_perm
        y = float(np.interp(v.at_m, distance, speed)) * KMH
        ax1.plot(v.at_m, y, "o", ms=14, color="#c0392b", label= " max. Überschreitung" if i == 0 else None)  # v is the arrow shape
        ax1.annotate(f"+{v.max_excess_ms * KMH:.1f} km/h", xy=(v.at_m, y),
                    xytext=(8, 10), textcoords="offset points",
                    fontsize=11, color="#c0392b")
        
    spielraum = (v_perm - speed) * KMH

    ax2.plot(distance, spielraum, lw=1.6, color="#000000")
    ax2.axhline(0.0, color="#c0392b", lw=1.2)
    ax2.fill_between(distance, 0, spielraum, where=spielraum < 0, color="#c0392b", alpha=0.4)
    ax2.fill_between(distance, 0, spielraum, where=spielraum >= 0, color="#27ae60", alpha=0.2)
    ax2.set_xlabel("Weg [m]", fontsize=12)
    ax2.set_ylabel("spielraum [km/h]", fontsize=12)
    ax2.grid(alpha=0.3)

    ax1.legend(loc="upper right", fontsize=10)

    fig.tight_layout()

    fig.savefig(args.out, dpi=150)

    return 1 if violations else 0

if __name__ == "__main__":
    sys.exit(main())


