import sys
import os

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.leagues_utils import fetch_and_insert_leagues

def run():
    fetch_and_insert_leagues()

if __name__ == "__main__":
    run()
