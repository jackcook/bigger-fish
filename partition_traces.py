import argparse
import pickle
import time
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Automate the collection of video player based CPU traces.')
    parser.add_argument("input")
    parser.add_argument("-o", required=True)
    args = parser.parse_args()
    
    data = []
    input_file_path = Path(args.input)
    with open(input_file_path, 'rb') as input_file:
        data = pickle.load(input_file)

    timetstamp = int(time.time())
    
    for i in range(len(data) // 100):
        partition = data[i * 100:i*100 + 100]

        out_path = Path(args.o or ".").joinpath(f"{input_file_path.name_i}")
        with open(out_path, "wb") as out_file:
            pickle.dump(partition, out_file)


if __name__ == "__main__":
    main()