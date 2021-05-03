import os
import json


SRC_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)))
MAIN_DIR = os.path.join(SRC_DIR, "..")
RESOURCE_DIR = os.path.join(MAIN_DIR, "resources")
IMG_DIR = os.path.join(RESOURCE_DIR, "images")
DESIGN_DIR = os.path.join(MAIN_DIR, "resources", "design")
CONFIG_DIR = os.path.join(MAIN_DIR, "config")

# true results
RESULT_STACK = {}

with open(os.path.join(CONFIG_DIR, "default.json"), "r") as f:
    DEFAULT = json.load(f)
