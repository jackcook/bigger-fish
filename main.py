from trace_collector import TraceCollector
from video_player import VideoPlayer, SupportedPlayers

import threading
import pickle
import argparse
import sys
import os
from tqdm import trange
import time
import platform

parser = argparse.ArgumentParser(description='Automate the collection of video player based CPU traces.')
parser.add_argument("--trace_len", type=int, default=1, help="The trace length for the recordings in seconds.")
parser.add_argument("--num_runs", type=int, default=5, help="The number of runs for each video file.")
parser.add_argument("--out_dir", type=str, default="", help="The output location.")
parser.add_argument("--var", choices=["codec", "player", "full"], default="codec", help="The variable that will be changed. \
        Choosing the codec will record traces for each codec and vice versa.")
opts = parser.parse_args()

NUM_OF_RUNS = opts.num_runs
TRACE_LENGTH = opts.trace_len
OUT_DIR = opts.out_dir
VAR = opts.var
VIDEO_FILES = ["sample.mp4", "sample.flv", "sample.3gp", "sample.mkv"]

def run(file_path, trace_length, player_type, browser="CHROME"):
    with TraceCollector(trace_length=trace_length) as collector:
        player = VideoPlayer(player=player_type)

        if browser == "FIREFOX":
            collector.setFirefox()
        if browser == "CHROME":
            collector.setChrome()
        if browser == "EDGE":
            collector.setEdge()
        if browser == "SAFARI":
            collector.setSafari()

        player_thread = threading.Thread(target=lambda: player.play(file_path, trace_length))
        player_thread.start()
        
        trace = collector.collect_traces()
        player_thread.join()
        return [trace, file_path, browser, player_type.name, platform.platform(), os.getlogin(), int(time.time())]

def ensure_output_file_does_not_exist(out_file):
    if os.path.exists(out_file):
        print(f"Output file already exists: {out_file}")
        print("Would you like to overwrite it? (y/n)")
        if input().casefold() != "y".casefold():
            print("Exiting...")
            return False
    return True

def main():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)
    out_file = os.path.join(OUT_DIR, fr"traces_{NUM_OF_RUNS}_runs_{TRACE_LENGTH}_{sys.platform}_{int(time.time())}.pkl")
    if not ensure_output_file_does_not_exist(out_file):
        return

    video_player = VideoPlayer()

    traces = []

    if opts.var == "player":
        for player in video_player.players:
            video_player = VideoPlayer(player=player)
            file = "sample.mp4"
            print(f"Recording traces for {file} with {player.name}...")
            for _ in trange(NUM_OF_RUNS):
                trace = run(file, TRACE_LENGTH, video_player)
                traces.append(trace)

    elif opts.var == "codec":
        for file_path in VIDEO_FILES:
            print(f"Playing {file_path}...")
            for _ in trange(NUM_OF_RUNS):
                run(file_path, TRACE_LENGTH, video_player)

    elif opts.var == "full":
        if platform.system()== "Darwin":
            browsers = ["SAFARI","FIREFOX", "CHROME"]
        else:
            browsers = ["EDGE","FIREFOX", "CHROME"]

        for video_file_path in VIDEO_FILES:
            for browser in browsers:
                for player in SupportedPlayers:
                    out_file = os.path.join(OUT_DIR, fr"traces_{NUM_OF_RUNS}_runs_{TRACE_LENGTH}_{sys.platform}_{video_file_path}_{browser}_{player}_{int(time.time())}.pkl")
                    traces = []
                    for _ in trange(NUM_OF_RUNS):
                        print(f"Run: {video_file_path, browser, player}")
                        trace = run(video_file_path, TRACE_LENGTH, player, browser)
                        traces.append(trace)
                    with open(out_file, "wb") as f:
                        pickle.dump(traces, f)


if __name__ == "__main__":
    main()