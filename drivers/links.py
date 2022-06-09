import os
import subprocess

class LinksDriver:

    def _kill(self):
        subprocess.Popen(["pkill", "links"])

    def get(self, url):
        self._kill()
        os.system('cls' if os.name == 'nt' else 'clear')
        subprocess.Popen(["links", url])

    def quit(self):
        self._kill()