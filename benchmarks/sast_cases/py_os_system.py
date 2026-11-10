import os


def ping(host: str) -> None:
    os.system("ping -c 1 " + host)
