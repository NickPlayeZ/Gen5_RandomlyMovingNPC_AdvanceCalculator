from collections import defaultdict
from functools import reduce


# ===========================================================
# CONFIGURATION
# ===========================================================

COOLDOWN_PROBS = [
    (16, 0.25),
    (32, 0.25),
    (48, 0.25),
    (64, 0.25),
]

EPS = 1e-12

# Predefined NPC types (1–21)
# type1 = special no-break logic
# type2 = special always-1-break logic
# type3 = 1/8-frame break logic with given probability
NPC_TYPE_DATA = {
    1: ("type1", None),
    2: ("type2", None),

    3: ("type3", 0.3333),
    4: ("type3", 0.7500),
    5: ("type3", 0.6667),
    6: ("type3", 0.6000),
    7: ("type3", 0.5714),
    8: ("type3", 0.5000),
    9: ("type3", 0.4167),
    10: ("type3", 0.3333),
    11: ("type3", 0.2917),
    12: ("type3", 0.2667),
    13: ("type3", 0.2381),
    14: ("type3", 0.2500),
    15: ("type3", 0.1548),
    16: ("type3", 0.3333),
    17: ("type3", 0.5000),
    18: ("type3", 0.3750),
    19: ("type3", 0.2222),
    20: ("type3", 0.4375),
    21: ("type3", 0.4333),
}

TIME_WINDOWS = [
    ("Loading into the game", 40),
    ("Sweet Scent", 75),
    ("Honey", 54),
    ("b-out menu static/egg", 2),
    ("x-out party static/egg", 1),
    ("b-out menu phenomena (step)", 11),
    ("x-out party phenomena (step)", 10),
    ("b-out menu step encounter (turn)", 7),
    ("x-out party step encounter (turn)", 6),
    ("b-out menu Lati@s (step)", 10),
    ("x-out party Lati@s (step)", 9),
]



# ===========================================================
# SAFE INPUT
# ===========================================================

def safe_input_int(prompt, allowed=None):
    while True:
        val = input(prompt).strip()
        try:
            num = int(val)
            if allowed and num not in allowed:
                print(f"Please enter one of {allowed}")
                continue
            return num
        except ValueError:
            print("Please enter a valid integer.")


# ===========================================================
# CORE PROBABILITY ENGINE
# ===========================================================

def events_distribution_for_L(W, L, event_phases):
    event_phases = set(event_phases)
    dist = defaultdict(float)

    for offset in range(L):
        count = 0
        for t in range(W):
            if (offset + t) % L in event_phases:
                count += 1
        dist[count] += 1 / L

    return dist


def single_npc_distribution(W, special_type, p_break1):
    dist_events_total = defaultdict(float)

    # ---- TYPE 1: old special logic ----
    if special_type == "type1":
        for c, pc in COOLDOWN_PROBS:
            dist_L = events_distribution_for_L(W, c, [0])
            for e, p in dist_L.items():
                dist_events_total[e] += pc * p
        factor = 2

    # ---- TYPE 2: old special logic ----
    elif special_type == "type2":
        for c, pc in COOLDOWN_PROBS:
            L = c + 1
            phases = [0, L - 1]
            dist_L = events_distribution_for_L(W, L, phases)
            for e, p in dist_L.items():
                dist_events_total[e] += pc * p
        factor = 1

    # ---- TYPE 3: break=1 or break=8 with given probability ----
    else:
        p_break8 = 1 - p_break1

        for c, pc in COOLDOWN_PROBS:

            # break = 1
            if p_break1 > 0:
                L1 = c + 1
                phases = [0, L1 - 1]
                dist_L1 = events_distribution_for_L(W, L1, phases)
                for e, p in dist_L1.items():
                    dist_events_total[e] += pc * p_break1 * p

            # break = 8
            if p_break8 > 0:
                L8 = c + 8
                phases = [0, L8 - 8]
                dist_L8 = events_distribution_for_L(W, L8, phases)
                for e, p in dist_L8.items():
                    dist_events_total[e] += pc * p_break8 * p

        factor = 1

    # Convert to advances
    max_events = max(dist_events_total.keys()) if dist_events_total else 0
    max_adv = max_events * factor

    dist_adv = [0.0] * (max_adv + 1)
    for e, p in dist_events_total.items():
        dist_adv[e * factor] += p

    return dist_adv


def convolve(d1, d2):
    res = [0.0] * (len(d1) + len(d2) - 1)
    for i, a in enumerate(d1):
        if a == 0:
            continue
        for j, b in enumerate(d2):
            if b == 0:
                continue
            res[i + j] += a * b
    return res


# ===========================================================
# MAIN PROGRAM
# ===========================================================

def main():
    print("=== RNG Advance Distribution Calculator ===")

    npc_count = safe_input_int("Number of NPCs in area: ")

    npc_specs = []
    for i in range(npc_count):
        t = safe_input_int(f"NPC {i+1} type (1–21): ", allowed=list(NPC_TYPE_DATA.keys()))
        special_type, p_break1 = NPC_TYPE_DATA[t]
        npc_specs.append((special_type, p_break1))

    # Compute NPC distributions for each window
    all_window_results = []

    for name, W in TIME_WINDOWS:
        dists = []
        for special_type, p_break1 in npc_specs:
            if special_type == "type3":
                dist = single_npc_distribution(W, special_type, p_break1)
            else:
                dist = single_npc_distribution(W, special_type, None)
            dists.append(dist)

        total = dists[0]
        for d in dists[1:]:
            total = convolve(total, d)

        all_window_results.append((name, W, total))

    # Determine the max number of rows needed
    max_rows = max(len(dist) for (_, _, dist) in all_window_results)

    print("\n===================================================")
    print("    RESULTS — SIDE-BY-SIDE TABLES (Sheets Ready)")
    print("===================================================\n")

    # Header row
    header_parts = []
    for (name, W, _) in all_window_results:
        header_parts.append(f"{name} ({W})\t")
        header_parts.append("\t")
        header_parts.append("\t")
    print("".join(header_parts))

    # Column labels row
    label_parts = []
    for _ in all_window_results:
        label_parts.append("Advance\tPercent\t\t")
    print("".join(label_parts))

    # Data rows
    for r in range(max_rows):
        row_parts = []
        for (_, _, dist) in all_window_results:
            if r < len(dist):
                adv = r
                p = dist[r] * 100
                row_parts.append(f"{adv}\t{p:.12f}\t\t")
            else:
                row_parts.append("\t\t\t")
        print("".join(row_parts))


# ===========================================================
# ENTRY POINT
# ===========================================================

if __name__ == "__main__":
    main()
