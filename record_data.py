import os

if "DISPLAY" not in os.environ:
    # Start selenium on main display if starting experiment over SSH
    os.environ["DISPLAY"] = ":0"

from enum import Enum

import argparse
import ctypes
import json
import logging
import math
import os
import pickle
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time

from drivers import LinksDriver, RemoteDriver, SafariDriver

from flask import Flask, send_from_directory
from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException, TimeoutException
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm
from urllib3.exceptions import MaxRetryError, ProtocolError

import pandas as pd


class Browser(Enum):
    CHROME = "chrome"
    CHROME_HEADLESS = "chrome_headless"
    FIREFOX = "firefox"
    SAFARI = "safari"
    LINKS = "links"
    REMOTE = "remote"
    TOR_BROWSER = "tor_browser"

    def __str__(self):
        return self.name.lower()

    def get_new_tab_url(self):
        if self == Browser.CHROME or self == Browser.CHROME_HEADLESS:
            return "chrome://new-tab-page"
        elif self == Browser.FIREFOX:
            return "about:home"
        elif self == Browser.SAFARI:
            return "favorites://"
        elif self == Browser.LINKS:
            raise NotImplementedError()
        elif self == Browser.REMOTE:
            return "biggerfish://new-tab"
        elif self == Browser.TOR_BROWSER:
            return "about:blank"


parser = argparse.ArgumentParser(
    description="Automate the collection of browser-based CPU traces."
)
parser.add_argument(
    "--browser",
    type=Browser,
    choices=list(Browser),
    default="chrome",
    help="The browser to use for the victim process.",
)
parser.add_argument("--num_runs", type=int, default=100)
parser.add_argument(
    "--attacker_type",
    type=str,
    choices=["javascript", "javascript_cache", "counter", "ebpf"],
    default="counter",
)
parser.add_argument(
    "--javascript_attacker_type", type=str, choices=["ours", "cache"], default="ours"
)
parser.add_argument(
    "--trace_length",
    type=int,
    default=15,
    help="The length of each recorded trace, in seconds.",
)
parser.add_argument(
    "--sites_list",
    type=str,
    default="alexa100",
    help="The list of sites to use. If using top n U.S. Alexa sites, should be alexan, where n >= 1.",
)
parser.add_argument(
    "--receiver_ip",
    type=str,
    default="0.0.0.0",
    help="The address of the receiver, if we're using one.",
)
parser.add_argument(
    "--receiver_port",
    type=int,
    default=1234,
    help="The port of the receiver, if we're using one.",
)
parser.add_argument(
    "--out_directory", type=str, default="data", help="The output directory name."
)
parser.add_argument(
    "--timer_resolution",
    type=float,
    default=None,
    help="Resolution of the timer during counter attacks. e.g. if set to 0.001, rounds to nearest millisecond.",
)
parser.add_argument(
    "--enable_timer_jitter",
    type=bool,
    default=False,
    help="True if we want to enable Chrome's jitter algorithm during counter attacks.",
)
parser.add_argument(
    "--twilio_interval",
    type=float,
    default=0.1,
    help="Interval at which to send updates with Twilio. e.g. if set to 0.1, will send a text each time another 10%% of the traces are collected. Set to 0 to disable.",
)
parser.add_argument(
    "--overwrite",
    type=bool,
    default=False,
    help="True if we want to overwrite the output directory.",
)
parser.add_argument(
    "--disable_chrome_sandbox",
    type=bool,
    default=False,
    help="True if we want to disable Chrome's sandbox. browser must be set to chrome or chrome_headless.",
)
parser.add_argument(
    "--tor_browser_path",
    type=str,
    help="Path to the Tor Browser bundle. browser must be set to tor_browser.",
)
parser.add_argument(
    "--tor_onion_address",
    type=str,
    help="Onion address to use to access attacker over Tor.",
)
parser.add_argument(
    "--enable_cache_countermeasure",
    type=bool,
    default=False,
    help="True if we want to enable the cache countermeasure Chrome extension.",
)
parser.add_argument(
    "--enable_interrupts_countermeasure",
    type=bool,
    default=False,
    help="True if we want to enable the interrupts countermeasure Chrome extension.",
)
parser.add_argument(
    "--enable_timer_countermeasure",
    type=bool,
    default=False,
    help="True if we want to enable the randomized timer countermeasure.",
)
parser.add_argument(
    "--chrome_binary_path",
    type=str,
    default=None,
    help="Path to a directory containing chrome and chromedriver binaries, if desired.",
)
parser.add_argument(
    "--ebpf_ns_threshold",
    type=int,
    default=500,
    help="Minimum gap duration to record interrupts with eBPF tool.",
)
opts = parser.parse_args()

if opts.sites_list == "open_world" and opts.num_runs != 1:
    print("If sites_list = open_world, num_runs must equal 1.")
    sys.exit(1)

if (
    opts.disable_chrome_sandbox
    and opts.browser != Browser.CHROME
    and opts.browser != Browser.CHROME_HEADLESS
):
    print(
        "You can't set disable_chrome_sandbox to true unless browser is chrome or chrome_headless."
    )
    sys.exit(1)

if opts.browser == Browser.REMOTE and (
    opts.receiver_ip is None or opts.receiver_port is None
):
    print("If browser is remote, must pass receiver_ip and receiver_port.")
    sys.exit(1)

if opts.attacker_type == "ebpf":
    # Get root access before running rest of the script
    subprocess.call(["sudo", "whoami"], stdout=subprocess.PIPE)

if (
    opts.tor_browser_path is not None or opts.tor_onion_address is not None
) and opts.browser != Browser.TOR_BROWSER:
    print(
        "You can't set tor_browser_path or tor_onion_address without setting browser to tor_browser."
    )
    sys.exit(1)

if opts.browser == Browser.TOR_BROWSER and (
    opts.tor_browser_path is None or opts.tor_onion_address is None
):
    print(
        "If browser is tor_browser, tor_browser_path and tor_onion_address must be set."
    )
    sys.exit(1)

if opts.enable_timer_jitter and opts.timer_resolution is None:
    print("If enable_timer_jitter is true, timer_resolution must be set.")
    sys.exit(1)

if opts.timer_resolution is not None and not os.path.exists(
    os.path.join("lib", "libtimer.so")
):
    print("libtimer.so needs to be compiled. Run:")
    print("cc -fPIC -shared -o lib/libtimer.so lib/timer.c")
    sys.exit(1)

if opts.enable_timer_countermeasure and opts.attacker_type != "javascript":
    print(
        "If enable_timer_countermeasure is true, attacker_type must be set to javascript."
    )
    sys.exit(1)


def confirm(prompt):
    response = input(f"{prompt} [y/N] ")

    if "y" not in response.lower():
        sys.exit(1)


remote_driver = None

if opts.timer_resolution is not None:
    c_lib = ctypes.CDLL(os.path.join(os.getcwd(), "lib", "libtimer.so"))
    c_lib.configure_timer.argtypes = [ctypes.c_double, ctypes.c_bool]
    c_lib.configure_timer(opts.timer_resolution, opts.enable_timer_jitter)
    c_lib.timer.restype = ctypes.c_double


def get_attacker_url():
    if opts.browser == Browser.TOR_BROWSER:
        if not opts.tor_onion_address.startswith("http://"):
            return f"http://{opts.tor_onion_address}"

        return opts.tor_onion_address
    else:
        return "http://localhost:1234"


def get_driver(browser):
    global remote_driver

    if browser == Browser.LINKS:
        return LinksDriver()
    elif browser == Browser.REMOTE:
        if remote_driver is None:
            remote_driver = RemoteDriver(opts.receiver_ip, opts.receiver_port)

        return remote_driver
    if browser == Browser.SAFARI:
        return SafariDriver(get_attacker_url())
    elif browser == Browser.TOR_BROWSER:
        from tbselenium.tbdriver import TorBrowserDriver

        return TorBrowserDriver(opts.tor_browser_path)

    driver_cls = getattr(
        webdriver, browser.name[0] + browser.name[1:].split("_")[0].lower()
    )

    if browser == Browser.CHROME or browser == Browser.CHROME_HEADLESS:
        chrome_opts = Options()

        if opts.chrome_binary_path is not None:
            chrome_opts.binary_location = os.path.join(
                opts.chrome_binary_path, "chrome"
            )

        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.add_argument("--ignore-ssl-errors")
        chrome_opts.add_argument("--ignore-certificate-errors")

        if opts.enable_cache_countermeasure:
            chrome_opts.add_extension(os.path.join("extensions", "cache.crx"))

        if opts.enable_interrupts_countermeasure:
            chrome_opts.add_extension(os.path.join("extensions", "interrupts.crx"))

        if opts.sites_list == "open_world":
            chrome_opts.add_argument("--disable-browser-side-navigation")

        if browser == Browser.CHROME:
            chrome_opts.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
        elif browser == Browser.CHROME_HEADLESS:
            chrome_opts.add_argument("--headless")

        # chromedriver needs this flag when running as root
        if os.geteuid() == 0 or opts.disable_chrome_sandbox:
            chrome_opts.add_argument("--no-sandbox")

        if opts.chrome_binary_path is not None:
            return driver_cls(
                options=chrome_opts,
                executable_path=os.path.join(opts.chrome_binary_path, "chromedriver"),
            )
        else:
            return driver_cls(options=chrome_opts)

    return driver_cls()


# Make sure existing processes aren't running
procs = subprocess.check_output(["ps", "aux"]).decode("utf-8").split("\n")

for term in ["python", "chrome", "safaridriver"]:
    conflicts = []

    for p in procs:
        if (
            len(p) < 2
            or not p.split()[1].isnumeric()
            or os.getpid() == int(p.split()[1])
        ):
            continue

        if term.lower() in p.lower():
            conflicts.append(p)

    if len(conflicts) > 0:
        print()
        print("Processes")
        print("=========")
        print("\n".join(conflicts))
        confirm(
            f"Potentially conflicting {term} processes are currently running. OK to continue?"
        )

# Double check that we're not overwriting old data
if not opts.overwrite and os.path.exists(opts.out_directory):
    print(
        f"WARNING: Data already exists at {opts.out_directory}. What do you want to do?"
    )
    res = input("[A]ppend [C]ancel [O]verwrite ").lower()

    if res == "a":
        pass
    elif res == "o":
        confirm(
            f"WARNING: You're about to overwrite {opts.out_directory}. Are you sure?"
        )
        shutil.rmtree(opts.out_directory)
    else:
        sys.exit(1)
elif opts.overwrite:
    shutil.rmtree(opts.out_directory)

if not os.path.exists(opts.out_directory):
    os.mkdir(opts.out_directory)

# Optionally set up SMS notifications
using_twilio = False

if opts.twilio_interval != 0:
    if os.path.exists("twilio.json"):
        from twilio.rest import Client

        twilio_data = json.loads(open("twilio.json").read())
        twilio_client = Client(twilio_data["account_sid"], twilio_data["auth_token"])
        using_twilio = True
    else:
        print(
            "WARNING: No twilio.json file found, but twilio_interval > 0. Continuing anyway."
        )


def send_notification(message):
    if using_twilio:
        twilio_client.messages.create(
            body=message, from_=twilio_data["from"], to=twilio_data["to"]
        )


if (
    opts.attacker_type == "javascript"
    or opts.attacker_type == "javascript_cache"
    or opts.attacker_type == "sleep"
):
    # Start serving attacker app
    app = Flask(__name__)

    # Disable Flask logs
    os.environ["WERKZEUG_RUN_MAIN"] = "true"
    log = logging.getLogger("werkzeug")
    log.disabled = True

    @app.route("/")
    def root():
        return send_from_directory("attacker", "index.html")

    @app.route("/<path:path>")
    def static_dir(path):
        return send_from_directory("attacker", path)

    flask_thread = threading.Thread(target=app.run, kwargs={"port": 1234})
    flask_thread.setDaemon(True)
    flask_thread.start()

    if opts.browser != Browser.SAFARI:
        attacker_browser = get_driver(opts.browser)
        attacker_browser.get(get_attacker_url())

        attacker_browser.execute_script(
            f"window.trace_length = {opts.trace_length * 1000}"
        )
        attacker_browser.execute_script("window.using_automation_script = true")


def create_browser():
    browser = get_driver(opts.browser)
    browser.set_page_load_timeout(opts.trace_length)
    return browser


def get_time():
    if opts.timer_resolution is None:
        return time.time()
    else:
        return c_lib.timer()


def collect_data(q):
    data = [-1] * (opts.trace_length * 1000)
    trace_time = get_time() * 1000

    if opts.attacker_type == "counter":
        while True:
            datum_time = get_time() * 1000
            idx = math.floor(datum_time - trace_time)

            if idx >= len(data):
                break

            num = 0

            while get_time() * 1000 - datum_time < 5:
                num += 1

            data[idx] = num
    elif (
        opts.attacker_type == "javascript"
        or opts.attacker_type == "javascript_cache"
        or opts.attacker_type == "sleep"
    ):
        try:
            js_attacker_type = (
                ("ours_cm" if opts.enable_timer_countermeasure else "ours")
                if opts.attacker_type == "javascript"
                else ("sleep" if opts.attacker_type == "sleep" else "cache")
            )
            attacker_browser.execute_script(
                f'window.collectTrace("{js_attacker_type}")'
            )
        except InvalidSessionIdException:
            q.put([-1])
            return

        time.sleep(opts.trace_length)

        data = []

        while len(data) == 0:
            try:
                traces = attacker_browser.execute_script("return traces;")

                if len(traces) > 0:
                    data = traces[0]
            except Exception as e:
                print(e)
                q.put([-1])
                return
    elif opts.attacker_type == "ebpf":
        child = subprocess.run(
            [
                "sudo",
                "ebpf/target/release/ebpf",
                f"--timeout={opts.trace_length * 1000}",
                f"--ns-threshold={opts.ebpf_ns_threshold}",
            ],
            capture_output=True,
        )
        data = []

        lines = child.stdout.splitlines()
        data.append((-1, lines[0]))

        for line in lines[1:]:
            x = line.split()
            kind = x[0]
            x = list(map(lambda v: int(v), x[1:]))
            y = []

            for n in range(len(x) // 2):
                y.append((x[n * 2], x[n * 2 + 1]))

            data.append((kind, y))

    q.put(data)


def record_trace(url):
    q = queue.Queue()
    thread = threading.Thread(target=collect_data, name="record", args=[q])
    thread.start()

    start_time = time.time()

    try:
        browser.get(url)
    except TimeoutException:
        # Called when Selenium stops loading after the length of the trace
        pass
    except (MaxRetryError, ProtocolError):
        # Usually called on CTRL+C
        return None
    except Exception as e:
        print(type(e).__name__, e)
        return None

    sleep_time = opts.trace_length - (time.time() - start_time)

    if sleep_time > 0:
        time.sleep(sleep_time)

    thread.join()
    results = [q.get()]

    if len(results[0]) == 1 and results[0][0] == -1:
        return None

    if opts.browser == Browser.SAFARI and (
        opts.attacker_type == "javascript" or opts.attacker_type == "javascript_cache"
    ):
        browser.close()

    return results


recording = True


def signal_handler(sig, frame):
    global recording
    recording = False
    print("Wrapping up...")


signal.signal(signal.SIGINT, signal_handler)
using_custom_site = False


if opts.sites_list.startswith("alexa"):
    n = int(opts.sites_list.replace("alexa", ""))

    if n > 100:
        print("For sites_list, n must be less than or equal to 100.")
        sys.exit(1)

    domains = pd.read_csv(os.path.join("sites", "closed_world.csv"))["domain"].tolist()
    domains = [f"https://{x}" if "http://" not in x else x for x in domains]
    domains = domains[:n]
elif opts.sites_list == "open_world":
    domains = pd.read_csv(os.path.join("sites", "open_world.csv"))["domain"].tolist()
    domains = [f"https://{x}" for x in domains]
else:
    domains = opts.sites_list.split(",")
    domains = [f"https://{x}" for x in domains]
    using_custom_site = True


def should_skip(domain):
    out_f_path = os.path.join(
        opts.out_directory,
        f"{domain.replace('https://', '').replace('http://', '').replace('www.', '')}.pkl",
    )

    if os.path.exists(out_f_path):
        f = open(out_f_path, "rb")
        num_runs = 0

        while True:
            try:
                pickle.load(f)
                num_runs += 1
            except:
                break

        if num_runs == opts.num_runs:
            return True

    return False


def run(domain, update_fn=None):
    out_f_path = os.path.join(
        opts.out_directory,
        f"{domain.replace('https://', '').replace('http://', '').replace('www.', '')}.pkl",
    )
    out_f = open(out_f_path, "wb")
    i = 0

    # Add one so that we can have a first run where the site gets cached.
    while i < opts.num_runs + 1:
        if not recording:
            break

        if opts.browser == Browser.SAFARI and (
            opts.attacker_type == "javascript"
            or opts.attacker_type == "javascript_cache"
        ):
            pass
        else:
            try:
                browser.get(opts.browser.get_new_tab_url())
            except:
                pass

        trace = record_trace(domain)

        if trace is None:
            out_f.close()
            return False

        if i > 0 or opts.sites_list == "open_world":
            # Don't save first run -- site needs to be cached.
            data = (trace, domain)

            # Save data to output file incrementally -- this allows us to save much
            # more data than fits in RAM.
            pickle.dump(data, out_f)

            if update_fn is not None:
                update_fn()

            if opts.sites_list == "open_world":
                break

        i += 1

    out_f.close()
    return True


browser = None
total_traces = opts.num_runs * len(domains)

with tqdm(total=total_traces) as pbar:
    if using_twilio:
        notify_interval = opts.twilio_interval * total_traces
        last_notification = 0

    traces_collected = 0

    def post_trace_collection():
        global traces_collected, notify_interval, last_notification

        pbar.update(1)
        traces_collected += 1

        if using_twilio and traces_collected >= last_notification + notify_interval:
            send_notification(
                f"{twilio_data['name']} is done with {traces_collected / total_traces * 100:.0f}% of its current job!"
            )
            last_notification = traces_collected

    for i, domain in enumerate(domains):
        if not recording:
            break
        elif should_skip(domain):
            continue

        if (
            opts.browser == Browser.SAFARI
            and (
                opts.attacker_type == "javascript"
                or opts.attacker_type == "javascript_cache"
            )
            and browser is not None
        ):
            # Don't create a new browser in this case -- we will open a new
            # window instead due to limitations in safaridriver.
            pass
        else:
            browser = create_browser()

            if opts.browser == Browser.SAFARI:
                attacker_browser = browser

        success = run(domain, update_fn=post_trace_collection)

        if success:
            if opts.sites_list == "open_world" and traces_collected == 5000:
                break

            pbar.n = (i + 1) * opts.num_runs
            pbar.refresh()

        browser.quit()

if (
    opts.attacker_type == "javascript"
    or opts.attacker_type == "javascript_cache"
    or opts.attacker_type == "sleep"
):
    attacker_browser.quit()

if opts.sites_list == "open_world":
    browser.quit()

if opts.browser == Browser.SAFARI:
    try:
        browser.driver.quit()
    except:
        os.system("killall Safari")

if using_twilio:
    send_notification(f"{twilio_data['name']} is done with its job!")
