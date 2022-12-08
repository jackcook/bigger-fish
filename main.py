from trace_collector import TraceCollector
from video_player import VideoPlayer

import threading
import pickle

NUM_OF_RUNS = 1
TRACE_LENGTH = 5

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

with open("traces_{int(time.time())}.pkl", "wb") as file:
    pickle.dump(traces, file)