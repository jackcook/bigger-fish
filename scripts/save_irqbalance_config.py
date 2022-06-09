import argparse
import json
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--out_filename", type=str, required=True)
opts = parser.parse_args()

data = {}

for path in os.listdir("/proc/irq"):
    if not path.isnumeric():
        continue

    data[path] = open(f"/proc/irq/{path}/smp_affinity").read().strip()

with open(f"{opts.out_filename}.json", "w") as f:
    f.write(json.dumps(data, indent=4, sort_keys=True))