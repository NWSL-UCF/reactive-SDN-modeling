#!/bin/bash

# ===== Experiment parameters =====
START_RATE=0.1
END_RATE=3.0
STEP=0.1
DURATION=540
PKT_SIZE=1024
FLOW_ID=1
SRC_PORT=5007
DST_IP=10.0.0.2
DST_PORT=5012

MGEN_DIR="mgen_tmp"
LOG_DIR="logs"

mkdir -p "$MGEN_DIR"
mkdir -p "$LOG_DIR"

echo "Starting Poisson sweep from $START_RATE to $END_RATE pps"

rate=$START_RATE
while (( $(echo "$rate <= $END_RATE" | bc -l) )); do
    RATE_FMT=$(printf "%.1f" "$rate")

    MGEN_FILE="$MGEN_DIR/send_${RATE_FMT}pps.mgn"
    LOG_FILE="$LOG_DIR/send_${RATE_FMT}pps.log"

    echo "Running rate = $RATE_FMT pps for $DURATION seconds"

    # Generate MGEN script
    cat > "$MGEN_FILE" <<EOF
0.0 ON $FLOW_ID UDP SRC $SRC_PORT DST $DST_IP/$DST_PORT POISSON [$RATE_FMT $PKT_SIZE]
$DURATION OFF $FLOW_ID
EOF

    # Run MGEN
    mgen input "$MGEN_FILE" output "$LOG_FILE"

    rate=$(echo "$rate + $STEP" | bc)
done

echo "Poisson sweep completed