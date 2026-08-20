from dataclasses import dataclass
import numpy as np
import csv


@dataclass(frozen=True)
class SupervisionConfig:
    eoa_m: float = 2000.0
    decel_ms2: float = 0.7
    reaction_s: float = 3.0
    v_max_ms: float = 44.4
    warning_margin_ms: float = 1.4 
    # validation of defined read-only values:
    def __post_init__(self) -> None:
        if self.decel_ms2 <= 0.0:
            raise ValueError("decel_ms2 muss >0 sein")
        if self.reaction_s < 0.0:
            raise ValueError("reaction muss >= 0 sein")
        if self.v_max_ms < 0.0:
            raise ValueError("v_max muss >= 0 sein")
        if self.warning_margin_ms <= 0.0:
            raise ValueError("warning_margin_ms muss >= 0 sein")


def emergency_brake_curve(distance_m, cfg):
    distance_m = np.asarray(distance_m, dtype=float)
    a = cfg.decel_ms2
    eoa = cfg.eoa_m
    sub = np.maximum(eoa - distance_m, 0.0)
    v = np.sqrt(2*a*sub)
    return np.minimum(v, cfg.v_max_ms)

def permitted_speed(distance_m, cfg):
    distance_m = np.asarray(distance_m, dtype=float)
    a = cfg.decel_ms2
    T = cfg.reaction_s
    eoa = cfg.eoa_m
    sub = np.maximum(eoa - distance_m, 0.0)
    v = -a*T + np.sqrt(a*T*a*T + 2*a*sub)
    return np.minimum(v, cfg.v_max_ms)

def warning_speed(distance_m, cfg):
    distance_m = np.asarray(distance_m, dtype=float)
    perm_v = permitted_speed(distance_m, cfg)
    v_warn = np.maximum((perm_v - cfg.warning_margin_ms), 0.0)
    return np.minimum(v_warn, cfg.v_max_ms)


def simulate_run(cfg, v_cruise_ms= 33.3, brake_at_m=900.0,
                brake_decel_ms2=0.7, accel_ms2=0.6, dt_s=0.2):
    t, s, v = 0.0, 0.0, 0.0
    times,distances, speeds = [], [], []
    while s<= cfg.eoa_m + 50.0 and t < 1000.0:  # 1000.0 is a timing gaurd agains infinit loops
        times.append(t)
        distances.append(s)
        speeds.append(v)

        if s >= brake_at_m:  # should we decelerate?
            a = -brake_decel_ms2
        elif v < v_cruise_ms:  # did we reach cruising speed?
            a = accel_ms2
        else:   # if not both then we are cruising -> constant speed (a = 0.0)
            a = 0.0
        v = max(0.0, v + a*dt_s)
        s += v*dt_s
        t += dt_s

        if v == 0.0 and s >= brake_at_m:   # reached endpoint
            times.append(t)
            distances.append(s)
            speeds.append(v)
            break
    return np.array(times), np.array(distances), np.array(speeds) 
    # gives the arrays with all the times, distances and speeds to make the plot out of them given the chosed constants from the user

@dataclass(frozen=True)
class Violation:
    start_m: float
    end_m: float 
    max_excess_ms: float 
    at_m: float  # where the max_excess was

def find_violations(distance_m, speed_ms, limit_ms, tolerance_ms = 0.0):  # each one is an Array of its own and the values in similar indeces get compared together
    distance_m = np.asarray(distance_m, dtype=float)
    speed_ms = np.asarray(speed_ms, dtype = float)
    limit_ms = np.asarray(limit_ms, dtype = float)
    if not (distance_m.shape == speed_ms.shape == limit_ms.shape):
        raise ValueError("alle 3 arrays muessen gleich lang sein")
    
    excess = speed_ms - (limit_ms + tolerance_ms)   # generates an Array of excess values 
    over = excess > 0   # an array of bolean values for violation parts

    violations = []
    start = None   # index of beginning of the violation

    #or : for i, flag in enumerate(over, i=2): for example when man wants to start from a certain position
    for i, flag in enumerate(over):  #in the array "over" we have i which we can call as the index of the current iteration and flag which is the value in the array which is True or False
        if (flag) and (start is None):
            start = i  # violation begins here
        elif (not flag) and (start is not None):  # there was a violation and now it ended
            i0 = start
            i1 = i - 1 # end
            window = excess[i0 : i1 + 1]   # the sliced array for the area of the violation
            peak = int(np.argmax(window)) + i0  # argmax gibt index mit groste wert raus. + i0 cause this is the sliced array we want to know the index in the actual array
            violations.append(Violation(
                start_m = float(distance_m[i0]),
                end_m = float(distance_m[i1]),
                max_excess_ms = float(excess[peak]),
                at_m = float(distance_m[peak])
            ))
            start = None
    # after the for ends is start still not None? also the violation didn't end in the loop?
    if start is not None:
        i0 = start
        i1 = len(over)-1
        window = excess[i0 : i1 + 1]  # +1 is a must to ensure that the slicing isn't [5:5] for example
        peak = int(np.argmax(window)) +i0
        violations.append(Violation(
            start_m = float(distance_m[i0]),
            end_m = float(distance_m[i1]),
            max_excess_ms = float(excess[peak]),
            at_m = float(distance_m[peak])
        ))
    return violations


##### Opening files #####
# with: opens the file and guarantees it gets closed when the block ends, even if an exception fires partway through. Always use it; never bare open().
# mode "w" = write, overwrites existing content(optional). "r" = read (the default).
# newline="": required by the csv module specifically. 
# encoding="utf-8"
# fh is the file handle: the object you hand to the csv writer.

def write_run_csv(path, time_s, distance_m, speed_ms):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["time_s", "distance_m", "speed_ms"])  # writes the header in the csv file
        for row in zip(time_s, distance_m, speed_ms):  # the row form we want 
            writer.writerow([f"{value:.3f}" for value in row])  # writes the file with the given values by user and makes makes 3 decimals for readability


def read_run_csv(path):    # read what's wrote by write_run_csv and prints it if we want
    with open(path, newline="", encoding="utf-8") as fh:   # flag "r" is the default (optional)
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path} enthaelt keine Daten")
    return (
        np.array([float(r["time_s"]) for r in rows]),
        np.array([float(r["distance_m"]) for r in rows]),
        np.array([float(r["speed_ms"]) for r in rows])
    )

