"""OSBoard GUI entry point — pywebview + WebView2."""

import multiprocessing
import sys

from apps.web_gui import WebGUI

if __name__ == "__main__":
    multiprocessing.freeze_support()
    gui = WebGUI()
    gui.start()
