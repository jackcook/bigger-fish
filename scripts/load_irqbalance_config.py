import argparse
import json
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--config_path", type=str)
parser.add_argument("--cpu", default=-1, type=int)
opts = parser.parse_args()

if opts.cpu == -1 and opts.config_path is None:
    print("At least one of cpu or config_path must be set")
    sys.exit(1)

def update_smp_affinity(i, val):
    try:
        with open(f"/proc/irq/{i}/smp_affinity", "w") as f:
            f.write(val)
    except Exception as e:
        print(f"fail {i}")
        pass

if opts.cpu == -1:
    data = json.loads(open(f"{opts.config_path}.json", "r").read())

    for k in data:
        update_smp_affinity(k, data[k])
else:
    for path in os.listdir("/proc/irq"):
        if not path.isnumeric():
            continue

        update_smp_affinity(path, str(1 << opts.cpu))