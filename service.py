import os, sys

sys.path.insert(1, os.path.join(os.path.dirname(__file__), "resources", "lib"))

if __name__ == '__main__':
    from mainservice import MainService
    MainService()