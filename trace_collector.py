import time

from selenium import webdriver


class TraceCollector:
    def __init__(self, url="http://localhost:7777", trace_length=10, headless=False, sandbox=True):
        self.url = url
        self.trace_length = trace_length

        options = webdriver.chrome.options.Options()
        if headless:
            options.add_argument("--headless")
        if not sandbox:
            options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(options=options)

    def collect_traces(self):
        self.__run()
        self.driver.execute_script('window.collectTrace("ours")')
        time.sleep(self.trace_length)
        return self.__get_traces()

    def __get_traces(self) -> list:
        while True:
            traces = self.driver.execute_script("return traces;")
            if len(traces):
                return traces[0]

    def __run(self):
        self.driver.get(self.url)
        self.driver.execute_script(f"window.trace_length = {self.trace_length * 1000}")
        self.driver.execute_script("window.using_automation_script = true")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()


if __name__ == "__main__":
    with TraceCollector(trace_length=5) as collector:
        traces = collector.collect_traces()
        print(traces)
        time.sleep(3)
        traces = collector.collect_traces()
        print(traces)
