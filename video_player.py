import subprocess
import time
import sys

from enum import Enum


class SUPPORTED_PLAYERS(Enum):
    WINDOWS_MEDIA_PLAYER = 1
    MPC = 2
    VLC = 3


class VideoPlayer:
    def __init__(self, player=SUPPORTED_PLAYERS.VLC):
        pass

    def play(self, file_path, length):
        player_name = {"linux": "vlc", "win32": "vlc.exe", "darwin": "vlc"}[sys.platform]
        player = subprocess.Popen([player_name, file_path], stderr=subprocess.DEVNULL)
        time.sleep(length)
        player.kill()