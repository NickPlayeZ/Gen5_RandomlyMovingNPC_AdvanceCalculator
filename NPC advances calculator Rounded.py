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
    ("b-out menu Lati@s (step)", 8),
    ("7-frame step (Lati@s x-out + StepEnc b-out)", 7),
    ("b-out menu phenomena (step)", 11),
    ("x-out party phenomena (step)", 10),
    ("x-out party step encounter (turn)", 6),
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

    # ---- TYPE 1: special no-break logic ----
    if special_type == "type1":
        for c, pc in COOLDOWN_PROBS:
            dist_L = events_distribution_for_L(W, c, [0])
            for e, p in dist_L.items():
                dist_events_total[e] += pc * p
        factor = 2

    # ---- TYPE 2: always 1-frame break (two events per cycle) ----
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

    # Convert events → advances
    if dist_events_total:
        max_events = max(dist_events_total.keys())
    else:
        max_events = 0
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

    # Compute distributions per window
    window_infos = []  # each: dict with all needed info per window

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

        dist = total
        # Full possible advances: indices with p > EPS
        full_indices = [i for i, p in enumerate(dist) if p > EPS]
        if not full_indices:
            # No probability mass? (shouldn't happen) – fallback
            full_min = 0
            full_max = 0
        else:
            full_min = min(full_indices)
            full_max = max(full_indices)

        # Display range: advances with >=1% chance
        signif_indices = [i for i, p in enumerate(dist) if p * 100 >= 1.0 - 1e-9]

        if signif_indices:
            min_show = min(signif_indices)
            max_show = max(signif_indices)
        else:
            # If no advances reach 1%, show the full range
            min_show = full_min
            max_show = full_max

        height = max_show - min_show + 1  # number of data rows (adv lines)

        window_infos.append({
            "name": name,
            "W": W,
            "dist": dist,
            "full_min": full_min,
            "full_max": full_max,
            "min_show": min_show,
            "max_show": max_show,
            "height": height
        })

    # For printing side-by-side: each table has height+1 (data + possible advances line)
    max_height = max(info["height"] + 1 for info in window_infos)

    print("\n===================================================")
    print("    RESULTS — SIDE-BY-SIDE TABLES (Sheets Ready)")
    print("===================================================\n")

    # Header row: window names
    header_parts = []
    for info in window_infos:
        name = info["name"]
        W = info["W"]
        header_parts.append(f"{name} ({W})\t")
        header_parts.append("\t")
        header_parts.append("\t")  # spacer
    print("".join(header_parts))

    # Second header row: column labels
    label_parts = []
    for _ in window_infos:
        label_parts.append("Advances\tOdds in %\t\t")
    print("".join(label_parts))

    # Data rows + possible-advances row
    for r in range(max_height):
        row_parts = []
        for info in window_infos:
            dist = info["dist"]
            min_show = info["min_show"]
            max_show = info["max_show"]
            full_min = info["full_min"]
            full_max = info["full_max"]
            data_height = info["height"]  # number of data rows

            if r < data_height:
                adv = min_show + r
                if 0 <= adv < len(dist):
                    p = dist[adv] * 100
                else:
                    p = 0.0
                row_parts.append(f"{adv}\t{p:.2f}\t\t")
            elif r == data_height:
                # possible advances line
                row_parts.append(f"possible advances: {full_min}-{full_max}\t\t\t")
            else:
                # beyond this table's height: blank
                row_parts.append("\t\t\t")

        print("".join(row_parts))


# ===========================================================
# ENTRY POINT
# ===========================================================

if __name__ == "__main__":
    main()
