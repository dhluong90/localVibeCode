import subprocess


def ping(host: str) -> None:
    subprocess.run(
        "ping -c 1 " + host,
        shell = True,
    )
