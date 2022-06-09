from selenium import webdriver

class SafariDriver:

    def __init__(self, attacker_url):
        self.driver = webdriver.Safari()
        self.driver.get(attacker_url)

        self.main_window_handle = self.driver.current_window_handle
    
    def close(self):
        windows = self.driver.window_handles

        for window in windows:
            if window != self.main_window_handle:
                self.driver.switch_to.window(window)
                break

        self.driver.close()
        self.driver.switch_to.window(self.main_window_handle)

    def execute_script(self, script):
        return self.driver.execute_script(script)

    def get(self, url):
        self.driver.execute_script(
            f"window.open('{url}', '_blank', 'toolbar=1,location=1,menubar=1')")

    def set_page_load_timeout(self, timeout):
        self.driver.set_page_load_timeout(timeout)
    
    def quit(self):
        pass