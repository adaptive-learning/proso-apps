class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def info(msg):
    print(bcolors.OKGREEN + msg + bcolors.ENDC)


def error(msg):
    print(bcolors.FAIL + msg + bcolors.ENDC)
