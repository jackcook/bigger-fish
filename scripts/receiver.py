import os

if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"

import argparse
import socket

from selenium import webdriver
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument("--trace_length", type=int, default=15)
opts = parser.parse_args()

driver = webdriver.Chrome()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 1234))
s.listen(1)

print("Waiting for connection...")
conn, _ = s.accept()

print("Connected successfully!")

while True:
    chunk = conn.recv(1024)

    if not chunk:
        driver.quit()
        break

    msgs = chunk.decode("utf-8").split("\n")

    for domain in msgs:
        if len(domain) == 0:
            continue

        data = urlparse(domain)

        if data.scheme == "biggerfish":
            if data.netloc == "restart":
                driver.quit()
                driver = webdriver.Chrome()
            elif data.netloc == "set-timeout":
                driver.set_page_load_timeout(int(data.path[1:]))
            elif data.netloc == "new-tab":
                domain = "chrome://new-tab-page"

        try:
            driver.get(domain)
        except:
            pass

conn.close()
