from trace_collector import TraceCollector
from video_player import VideoPlayer, SupportedPlayers

import threading
import pickle
import argparse
import sys
import os
from tqdm import trange, tqdm
import time
import platform

parser = argparse.ArgumentParser(description='Automate the collection of video player based CPU traces.')
parser.add_argument("--len", type=int, default=15, help="The trace length for the recordings in seconds.")
parser.add_argument("--samples", type=int, default=5, help="The number of runs for each video file.")
parser.add_argument("--out_dir", type=str, default="", help="The output location.")
parser.add_argument("--codecs", choices=["3gp", "flv", "mp4", "mkv", "*"], nargs="+")
parser.add_argument("--browsers", choices=["chrome", "safari", "edge", "firefox", "*"], nargs="+")
parser.add_argument("--players", choices=["mpv", "mplayer", "vlc", "*"], nargs="+")
opts = parser.parse_args()

def run(file_path, trace_length, player_type, browser="CHROME"):
    with TraceCollector(trace_length=trace_length) as collector:
        player = VideoPlayer(player=player_type)

        if browser.upper() == "FIREFOX":
            collector.setFirefox()
        if browser.upper() == "CHROME":
            collector.setChrome()
        if browser.upper() == "EDGE":
            collector.setEdge()
        if browser.upper() == "SAFARI":
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

def combinations(players, codecs, browsers):
    total = []
    for codec in codecs:
        for player in players:
            for browser in browsers:
                total.append((codec, player, browser))
    return total

def main():
    opts = parser.parse_args()
    out_dir = opts.out_dir
    num_of_samples = opts.samples
    trace_len = opts.len

    traces = []

    players = ["mpv", "mplayer", "vlc"] if "*" in opts.players else opts.players
    codecs = ["3gp", "flv", "mp4", "mkv"] if "*" in opts.codecs else opts.codecs
    browsers = ["chrome", "safari", "edge", "firefox"] if "*" in opts.browsers else opts.browsers

    for codec, player_name, browser in tqdm(combinations(players, codecs, browsers)):
    
        player = SupportedPlayers.map(player_name)
        video_file = f"sample.{codec}"
        print(f"\nRun: {video_file, browser, player.name}")
        out_file = os.path.join(out_dir, fr"traces_{num_of_samples}_runs_{trace_len}_sec_{codec}_{player.name}_{browser}_{sys.platform}_{os.getlogin()}_{int(time.time())}.pkl")
        traces = []
    
        for _ in trange(num_of_samples):
            trace = run(video_file, trace_len, player, browser)
            traces.append(trace)

        with open(out_file, "wb") as f:
            pickle.dump(traces, f)

if __name__ == "__main__":
    main()