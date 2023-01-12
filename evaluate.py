import argparse
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

    def insert(self, row):
        self._validate_trace(row[0])

        trace = row[0]
        codec, browser, player, platform, user, timestamp = row[1:]
        new_data_point = [*trace, codec, browser, player.name, platform, user, timestamp]
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

    def _generate_model(self, X, y, test_size=0.2):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, stratify=y)
        
        clf = RandomForestClassifier()
        clf = clf.fit(X_train, y_train)

        y_probs = clf.predict_proba(X_test)
        top1 = top_k_accuracy_score(y_test, y_probs, k=1)

        return top1

    def evaluate(self, target, relaxations):
        data_frame = self.warehouse.get_df()

        browser_choices = "*" if "browser" in relaxations else data_frame["browser"].unique()
        player_choices = "*" if "player" in relaxations else data_frame["player"].unique()
        codec_choices = "*" if "codec" in relaxations else data_frame["codec"].unique()
        platform_choices = "*" if "platform" in relaxations else data_frame["platform"].unique()
        user_choices = "*" if "user" in relaxations else data_frame["user"].unique()

        combinations = np.meshgrid(browser_choices, player_choices, codec_choices, platform_choices, user_choices)
        combinations = np.array(combinations).T.reshape(-1, 5)
        
        experiments = {}
        scores = {}
        for browser, player, codec, platform, user in tqdm(combinations):
            data_point_amount = 0
            for fold in tqdm(range(10)):
                sub_df = data_frame.loc[:]
                sub_df = self._filter_data_points(sub_df, browser, player, codec, platform, user)
                
                if (len(data_frame) == 0):
                    continue
                
                X, y = self._preprocess(sub_df.loc[:], target)
                data_point_amount = len(X)
                
                if (browser, player, codec, platform, user) not in experiments:
                    experiments[(browser, player, codec, platform, user)] = []

                experiments[(browser, player, codec, platform, user)].append(self._generate_model(X, y))
            samples = experiments[(browser, player, codec, platform, user)]
            mean = np.mean(samples) * 100
            stdev = np.std(samples) * 100
            scores[(browser, player, codec, platform, user)] = (mean, stdev)
            print(f"{browser}, {player}, {codec}, {platform}, {user} -> {data_point_amount} data points: {mean:.2f}% (+/- {stdev:.2f})")

        return scores

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("--target", choices=["codec", "player", "browser", "platform", "user"])
    parser.add_argument("--relax", choices=["codec", "player", "browser", "platform", "user"], nargs="*", default=[])
    opts = parser.parse_args()

    warehouse = Warehouse()

    print("Reading files...")
    for root, _, files in os.walk(opts.dir):
        for file in tqdm(files):
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
                for row in data:
                    warehouse.insert(row)

    print("Converting to pandas.DataFrame")
    warehouse.convert_to_df()

    evaluator = Evaluator(warehouse=warehouse)

    print("Starting the evaluation")
    scores = evaluator.evaluate(target=opts.target, relaxations=[opts.target, *opts.relax])
    
if __name__ == "__main__":
    main()