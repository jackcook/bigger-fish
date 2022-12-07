from trace_collector import TraceCollector
from video_player import VideoPlayer

import threading
import json

NUM_OF_RUNS = 1
TRACE_LENGTH = 10

traces = []


def run(file_path, trace_length):
    with TraceCollector(trace_length=trace_length) as collector:
        player = VideoPlayer()

        def play_file():
            player.play(file_path, trace_length)

        player_thread = threading.Thread(target=play_file)
        player_thread.start()
        trace = collector.collect_traces()
        traces.append([trace, file_path])
        player_thread.join()


for file in ["sample.3gp", "sample.flv", "sample.mkv", "sample.mp4"]:
    for _ in range(NUM_OF_RUNS):
        run(file, TRACE_LENGTH)

with open("traces", "w+") as file:
    json.dump(traces, file)