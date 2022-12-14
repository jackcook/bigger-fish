from trace_collector import TraceCollector
from video_player import VideoPlayer

import threading
import pickle
import argparse
import sys

parser = argparse.ArgumentParser(description='Automate the collection of video player based CPU taces.')
parser.add_argument("--trace_len", type=int, default=1, help="The trace length for the recordings in seconds.")
parser.add_argument("--num_runs", type=int, default=5, help="The number of runs for each video file.")
parser.add_argument("--out_dir", type=str, default="", help="The output location.")
opts = parser.parse_args()

NUM_OF_RUNS = opts.num_runs
TRACE_LENGTH = opts.trace_len
OUT_DIR = opts.out_dir

traces = []


def run(file_path, trace_length):
    with TraceCollector(trace_length=trace_length) as collector:
        player = VideoPlayer()

        player_thread = threading.Thread(target = lambda: player.play(file_path, trace_length))
        player_thread.start()

        trace = collector.collect_traces()
        traces.append([trace, file_path])
        player_thread.join()


for file in ["sample.3gp", "sample.flv", "sample.mkv", "sample.mp4"]:
    for _ in range(NUM_OF_RUNS):
        run(file, TRACE_LENGTH)

with open(fr"{OUT_DIR}/traces_{NUM_OF_RUNS}_runs_{TRACE_LENGTH}_sec_{sys.platform}_OS.pkl", "wb") as file:
    pickle.dump(traces, file)