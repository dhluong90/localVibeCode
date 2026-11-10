import subprocess


def ls(path: str) -> None:
    subprocess.run(["ls", path], check=True)
