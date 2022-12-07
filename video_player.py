import subprocess
import time

from enum import Enum


class SUPPORTED_PLAYERS(Enum):
    WINDOWS_MEDIA_PLAYER = 1
    MPC = 2
    VLC = 3


class VideoPlayer:
    def __init__(self, player=SUPPORTED_PLAYERS.VLC):
        pass

    def play(self, file_path, length):
        player = subprocess.Popen(["vlc.exe", file_path])
        time.sleep(length)
        player.kill()