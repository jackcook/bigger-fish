import argparse
import numpy as np
import pickle
import os
import warnings

warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import top_k_accuracy_score
from sklearn.model_selection import train_test_split
from tqdm import trange

parser = argparse.ArgumentParser()
parser.add_argument("--data_file", default="data", type=str)
parser.add_argument("--n", default=10, type=int)
parser.add_argument("--test_size", default=0.25, type=float)
opts = parser.parse_args()

def get_data(path):
    # Data preparation
    traces = []
    labels = []

    if os.path.isdir(path):
        # If directory, find all .pkl files
        filepaths = [os.path.join(path, x) for x in os.listdir(path) if x.endswith(".pkl")]
    elif os.path.isfile(path):
        # If single file, just use this one
        filepaths = [path]
    else:
        raise RuntimeError

    for file in filepaths:
        f = open(file, "rb")

        all_data = pickle.load(f)
        for data in all_data:
            traces_i, labels_i = data[0], data[1]
            if isinstance(traces_i[0], list):
                traces.extend(traces_i)
            else:
                traces.append(traces_i)

            labels.append(labels_i)

    traces = np.array(traces)

    # Convert labels from domain names to ints
    domains = list(set(labels))
    int_mapping = {x: i for i, x in enumerate(domains)}
    labels = [int_mapping[x] for x in labels]
    labels = np.array(labels)

    return traces, labels, domains


def get_accs(X, y, domains):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=opts.test_size, stratify=y)

    clf = RandomForestClassifier()
    clf = clf.fit(X_train, y_train)

    y_probs = clf.predict_proba(X_test)
    top1 = top_k_accuracy_score(y_test, y_probs, k=1)
    top5 = top_k_accuracy_score(y_test, y_probs, k=5)

    return [top1, top5]

print(f"Analyzing results from {opts.data_file}")

X, y, domains = get_data(opts.data_file)
accs = np.array([get_accs(X, y, domains) for _ in trange(opts.n)])
print()

top1 = accs[:, 0].mean()
top1_std = accs[:, 0].std()

top5 = accs[:, 1].mean()
top5_std = accs[:, 1].std()

print(f"Number of traces: {len(X)}")
print()
print("top1 accuracy: {:.1f}% (+/- {:.1f}%)".format(top1 * 100, top1_std * 100))
print("top5 accuracy: {:.1f}% (+/- {:.1f}%)".format(top5 * 100, top5_std * 100))
