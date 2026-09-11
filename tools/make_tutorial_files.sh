set -e
#
# Create the files the two tutorials register as assets, and print the digest
# the inference tutorial asks for.
#
# The download tutorial needs one file to hand out. The inference tutorial needs
# two: the dataset that stays behind the guardian, and the script that travels to
# it. The script's digest is what the owner's policy approves and what the FL
# client re-measures at redemption time, so it is printed here rather than left
# for the reader to derive.
#
# Safe to re-run: it overwrites all three files with the same content, so the
# digest does not move.

DATA_FILE=/tmp/asset_data.txt
COHORT_FILE=/tmp/patient_cohort.csv
SCRIPT_FILE=/tmp/inference_script.py

# ---- the download tutorial's dataset -------------------------------------
echo "The eagle lands at midnight." > "$DATA_FILE"

# ---- the inference tutorial's dataset ------------------------------------
# Never leaves the guardian's host; only the metrics computed over it come back.
cat > "$COHORT_FILE" <<'EOF'
patient_id,age,sex,hba1c,bmi,diagnosis
P001,54,F,7.8,31.2,type-2-diabetes
P002,61,M,6.4,27.9,prediabetes
P003,47,F,9.1,34.6,type-2-diabetes
P004,58,M,5.6,24.1,control
P005,66,F,8.3,29.8,type-2-diabetes
P006,52,M,6.9,30.4,prediabetes
P007,45,F,5.2,22.7,control
P008,70,M,8.8,33.1,type-2-diabetes
EOF

# ---- the inference tutorial's script -------------------------------------
# What the FL client would run against the cohort. It is registered as its own
# asset behind a public guardian, so the digest below is over exactly the bytes
# any party can fetch and check for themselves.
cat > "$SCRIPT_FILE" <<'EOF'
"""Cohort summary for a type-2 diabetes study.

Runs where the data is. Reads the cohort the guardian released to the FL client
on this host and reports aggregate metrics -- never rows.
"""

import csv
import sys


def summarize(rows):
    cases = [r for r in rows if r["diagnosis"] == "type-2-diabetes"]
    hba1c = [float(r["hba1c"]) for r in cases]
    return {
        "cohort_size": len(rows),
        "cases": len(cases),
        "mean_hba1c_in_cases": round(sum(hba1c) / len(hba1c), 2) if hba1c else None,
    }


def main():
    rows = list(csv.DictReader(sys.stdin))
    for name, value in summarize(rows).items():
        print(f"{name}={value}")


if __name__ == "__main__":
    main()
EOF

# ---- a second, different script ------------------------------------------
# The inference tutorial's last section presents this one under the first one's
# digest. The policy cannot tell the difference -- the credentials are in order
# -- so the only thing that catches it is the FL client re-measuring the code it
# actually received. One added line is enough to move the digest.
EDITED_FILE=/tmp/inference_script_v2.py
{
    echo "# v2: same analysis, one line of provenance added."
    cat "$SCRIPT_FILE"
} > "$EDITED_FILE"

DIGEST="sha256:$(sha256sum "$SCRIPT_FILE" | awk '{print $1}')"
EDITED_DIGEST="sha256:$(sha256sum "$EDITED_FILE" | awk '{print $1}')"

cat <<EOF
Tutorial files written.

  download tutorial  dataset : $DATA_FILE
  inference tutorial dataset : $COHORT_FILE
  inference tutorial script  : $SCRIPT_FILE
  the edited script          : $EDITED_FILE

The inference tutorial asks for the script's digest. It is:

  $DIGEST

The edited script hashes to something else, which is the whole point:

  $EDITED_DIGEST
EOF
