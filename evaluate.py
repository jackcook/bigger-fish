import argparse
from typing import Tuple
import csv
import time
import pandas
import os
import pickle
from pprint import pprint
from tqdm import tqdm
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import top_k_accuracy_score
from sklearn.model_selection import train_test_split, ShuffleSplit, cross_val_score

class Warehouse:
    def __init__(self):
        self.trace_len = -1 
        self.raw_data_points = []
        self.data_points = None

    def insert(self, row):
        self._validate_trace(row[0])

        trace = row[0]
        codec, browser, player, platform, user, timestamp = row[1:]
        if hasattr(player, "name"):
            player_name = player.name
        else:
            player_name = player
        new_data_point = [*trace, codec, browser, player_name, platform, user, timestamp]
        self.raw_data_points.append(new_data_point)

    def get_df(self):
        if self.data_points is None:
            self.convert_to_df()
        return self.data_points

    def convert_to_df(self):
        self.data_points = pandas.DataFrame(data=self.raw_data_points, columns=[*[f"{feature}" for feature in range(1,len(self.raw_data_points[0])-6+1)], "codec", "browser", "player", "platform", "user", "timestamp"])
        return self.data_points

    def _validate_trace(self, trace):
        if self.trace_len == -1:
            self.trace_len = len(trace)
        else:
            if self.trace_len != len(trace):
                raise Exception()

class Evaluator:
    def __init__(self, warehouse):
        self.warehouse: Warehouse = warehouse

    def _filter_data_points(self, df, browser, player, codec, platform, user) -> pandas.DataFrame:
        new_df = df.loc[:]

        if browser != "*":
            new_df = new_df[df["browser"] == browser]
        
        if codec != "*":
            new_df = new_df.loc[df["codec"] == codec]
        
        if player != "*":
            new_df = new_df.loc[df["player"] == player]

        if platform != "*":
            new_df = new_df.loc[df["platform"] == platform]

        if user != "*":
            new_df = new_df.loc[df["user"] == user]

        return new_df

    def _preprocess(self, df, target):
        le = LabelEncoder()
        for column in ["browser", "player", "codec", "platform", "user"]:
            df[column] = le.fit_transform(df[column])
        
        y = df[target]
        X = df.drop(columns=["browser", "player", "codec", "platform", "user", "timestamp"])

        return X, y

    def _predict(self, X, y, test_size=0.2):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, stratify=y)
        
        clf = RandomForestClassifier()
        clf = clf.fit(X_train, y_train)

        y_probs = clf.predict_proba(X_test)
        top1 = top_k_accuracy_score(y_test, y_probs, k=1)

        return top1

    def _create_samples(self, X, y, folds):
        samples = []
        for fold in tqdm(range(folds)):                
            accuracy = self._predict(X, y)
            samples.append(accuracy * 100)
        return samples

    def _get_statistics(self, samples) -> Tuple[float, float]:
        mean = -1
        stdev = -1

        if len(samples) > 0:
            mean = np.mean(samples)
            stdev = np.std(samples)
        return (mean, stdev)

    def _create_combinations(self, relaxations):
        data_frame = self.warehouse.get_df()

        browser_choices = "*" if "browser" in relaxations else data_frame["browser"].unique()
        player_choices = "*" if "player" in relaxations else data_frame["player"].unique()
        codec_choices = "*" if "codec" in relaxations else data_frame["codec"].unique()
        platform_choices = "*" if "platform" in relaxations else data_frame["platform"].unique()
        user_choices = "*" if "user" in relaxations else data_frame["user"].unique()

        combinations = np.meshgrid(browser_choices, player_choices, codec_choices, platform_choices, user_choices)
        combinations = np.array(combinations).T.reshape(-1, 5)

        return combinations

    def analyze(self, target, relaxations):
        data_frame = self.warehouse.get_df()
        combinations = self._create_combinations([target, *relaxations])
        
        def run():
            for browser, player, codec, platform, user in combinations:
                sub_df = self._filter_data_points(data_frame.loc[:], browser, player, codec, platform, user)
                data_point_amount = len(sub_df)
                
                yield (browser, player, codec, platform, user, data_point_amount)
        
        return run(), combinations

    def evaluate(self, target, relaxations, folds = 10):
        data_frame = self.warehouse.get_df()
        combinations = self._create_combinations(relaxations=[target, *relaxations])
        
        def run():
            for browser, player, codec, platform, user in combinations:
                sub_df = data_frame.loc[:]
                sub_df = self._filter_data_points(sub_df, browser, player, codec, platform, user)
                X, y = self._preprocess(sub_df.loc[:], target)

                data_point_amount = len(X)
                if data_point_amount == 0:
                    continue
                
                samples = []
                try:
                    samples = self._create_samples(X, y, folds)
                except ValueError as ex:
                    print("EXCEPTION HAPPENED WHEN", browser, player, codec, platform, user, data_point_amount)
                    print(ex)

                mean, stdev = self._get_statistics(samples)

                yield (browser, player, codec, platform, user, data_point_amount, mean, stdev, *samples)

        return run(), len(combinations)

def read_files(opts, warehouse: Warehouse):
    file_paths = []
    for root, _, files in os.walk(opts.dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)

    for file_path in tqdm(file_paths):
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
            for row in data:
                warehouse.insert(row)

def evaluate(evaluator, targets, relaxations, number_of_folds):
    print("Starting the evaluation")
    output_file_name = f"evaluations_{int(time.time())}.csv"

    header = ("target", "browser", "player", "codec", "platform", "user", "data_points", "mean", "stdev", *[f"fold_{i+1}" for i in range(number_of_folds)])
    write_line_to_csv(output_file_name, header)

    for target in targets:
        evaluations, total = evaluator.evaluate(target=target, relaxations=relaxations, folds=number_of_folds)
        for evaluation in tqdm(evaluations, total=total):
            browser, player, codec, platform, user, data_point_amount, mean, stdev = evaluation[:8]

            line = (target, *evaluation)
            if data_point_amount > 0:
                print(f"Target={target}", browser, player, codec, platform, user, data_point_amount, mean, stdev)

            write_line_to_csv(output_file_name, line)

def analyze(evaluator: Evaluator, targets, relaxations):
    print("Starting the analyzation")

    for target in targets:
        rows, _ = evaluator.analyze(target=target, relaxations=relaxations)
        for row in rows:
            browser, player, codec, platform, user, data_point_amount = row[:6]

            if data_point_amount > 0:
                print(f"Target={target}", row)

def write_line_to_csv(file, line):
    with open(file, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(line)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("--analyze",  action='store_true')
    parser.add_argument("--targets", choices=["codec", "player", "browser", "platform", "user", "*"], nargs="+")
    parser.add_argument("--relax", choices=["codec", "player", "browser", "platform", "user", "*"], nargs="*", default=[])
    parser.add_argument("--folds", default=10)
    opts = parser.parse_args()

    number_of_folds = int(opts.folds)
    targets = opts.targets
    if targets == ["*"]:
        targets = ["codec", "player", "browser", "platform", "user"]
    
    relaxations = opts.relax
    if relaxations == ["*"]:
        relaxations = ["codec", "player", "browser", "platform", "user"]

    warehouse = Warehouse()

    print("Reading files...")
    read_files(opts, warehouse)

    print("Converting to pandas.DataFrame...")
    warehouse.convert_to_df()

    evaluator = Evaluator(warehouse=warehouse)

    if opts.analyze:
        analyze(evaluator, targets=targets, relaxations=relaxations)
    else:
        evaluate(evaluator, targets=targets, relaxations=relaxations, number_of_folds=number_of_folds)

    
if __name__ == "__main__":
    main()