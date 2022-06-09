from alexa import alexa_domains

import numpy as np
import os
import pandas as pd
import urllib.request
import zipfile

if not os.path.exists("top-1m.csv"):
    urllib.request.urlretrieve("http://s3.amazonaws.com/alexa-static/top-1m.csv.zip", "top-1m.csv.zip")

    with zipfile.ZipFile("top-1m.csv.zip") as z:
        z.extractall()

existing_domains = domains = [f"{x.replace('!', '')}{'.com' if '.' not in x else ''}" for x in alexa_domains]
existing_names = set([x.replace("!", "").split(".")[0] for x in alexa_domains])

open_world_domains = []

df = pd.read_csv("top-1m.csv", header=None, names=["rank", "domain"])

for i in range(len(df)):
    domain = df.iloc[i]["domain"]

    if domain in existing_domains:
        continue
    elif domain.split(".")[0] in existing_names:
        continue
    else:
        open_world_domains.append(domain)
        existing_names.add(domain.split(".")[0])
    
    # Provide extra sites (we only need 5000) in case some sites have errors
    if len(open_world_domains) == 6000:
        break

pd.Series(open_world_domains).to_csv("open_world.csv", header=["domain"], index=False)