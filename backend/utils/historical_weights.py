"""
Historical alignment weights for strategy scoring.

These weights control how much historical patterns influence the final
strategy ranking. They are intentionally SMALL — historical data is
advisory, not a replacement for physics-based simulation.

Tuning guide:
    - All penalties/bonuses are in SECONDS added to/subtracted from total_time_s
    - A typical pit stop costs ~22s, so a 1s penalty is about 4.5% of a stop
    - The sum of all historical adjustments should rarely exceed +/- 3s
    - Set any weight to 0.0 to disable that factor
"""

# --- First Stop Timing ---
# Penalty when strategy's first stop is outside the historical IQR.
# Scales linearly with distance from IQR boundary.
FIRST_STOP_OUTSIDE_IQR_PENALTY_PER_LAP = 0.15  # seconds per lap outside IQR
FIRST_STOP_MAX_PENALTY_S = 2.0                   # cap total penalty

# --- Strategy Sequence Match ---
# Bonus (subtracted from time) when strategy matches a historically common
# compound sequence. Scaled by the historical frequency of that sequence.
SEQUENCE_MATCH_BONUS_S = 1.5       # max bonus for 100% frequency match
SEQUENCE_PARTIAL_MATCH_FACTOR = 0.4  # multiplier for partial matches

# --- Stop Count Alignment ---
# Small bonus when stop count matches the dominant historical pattern.
STOP_COUNT_ALIGNMENT_BONUS_S = 0.5

# --- Overall scaling ---
# Master multiplier for all historical adjustments. Set to 0.0 to
# completely disable historical influence without removing code.
HISTORICAL_WEIGHT_MASTER = 1.0
