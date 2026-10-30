"""Terminal UI styling and ANSI formatting for localVibeCode (zero dependencies)."""

from __future__ import annotations

import sys
from typing import Optional

USE_COLOR = sys.stdout.isatty()


class Colors:
    RESET = "\033[0m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    DIM = "\033[2m" if USE_COLOR else ""
    ITALIC = "\033[3m" if USE_COLOR else ""
    UNDERLINE = "\033[4m" if USE_COLOR else ""

    RED = "\033[31m" if USE_COLOR else ""
    GREEN = "\033[32m" if USE_COLOR else ""
    YELLOW = "\033[33m" if USE_COLOR else ""
    BLUE = "\033[34m" if USE_COLOR else ""
    MAGENTA = "\033[35m" if USE_COLOR else ""
    CYAN = "\033[36m" if USE_COLOR else ""
    WHITE = "\033[37m" if USE_COLOR else ""
    GRAY = "\033[90m" if USE_COLOR else ""


BANNER = f"""{Colors.CYAN}{Colors.BOLD}
  _                 _ __     ___ _          ___          _      
 | |   ___  __ __ _| |\\ \\   / (_) |__  ___ / __|___  __| |___  
 | |__/ _ \\/ _/ _` | | \\ \\ / /| | '_ \\/ -_) (__/ _ \\/ _` / -_) 
 |____\\___/\\__\\__,_|_|  \\_/  |_|_.__/\\___|\\___\\___/\\__,_\\___| 
{Colors.RESET}{Colors.GRAY}   Enterprise Local Vibe Coding Engine • 100% Offline • Graphify AST
{Colors.RESET}"""


def badge(label: str, color: str = Colors.GREEN) -> str:
    return f"{color}{Colors.BOLD}[{label}]{Colors.RESET}"


def info(msg: str) -> None:
    print(f"{badge('INFO', Colors.CYAN)} {msg}")


def success(msg: str) -> None:
    print(f"{badge('SUCCESS', Colors.GREEN)} {msg}")


def warning(msg: str) -> None:
    print(f"{badge('WARN', Colors.YELLOW)} {msg}")


def error(msg: str) -> None:
    print(f"{badge('ERROR', Colors.RED)} {msg}", file=sys.stderr)


def step(number: int | str, title: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}▶ Phase {number}:{Colors.RESET} {Colors.BOLD}{title}{Colors.RESET}")


def rule(title: Optional[str] = None, char: str = "─", width: int = 70) -> None:
    if title:
        rendered = f" {title} "
        remaining = max(0, width - len(rendered))
        left = remaining // 2
        right = remaining - left
        print(f"{Colors.GRAY}{char * left}{Colors.BOLD}{Colors.WHITE}{rendered}{Colors.RESET}{Colors.GRAY}{char * right}{Colors.RESET}")
    else:
        print(f"{Colors.GRAY}{char * width}{Colors.RESET}")
