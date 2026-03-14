from colorama import Fore, Style


def info(msg):
    print(f"{Fore.LIGHTBLUE_EX}{msg}{Style.RESET_ALL}")


def error(msg):
    print(f"{Fore.RED}{msg}{Style.RESET_ALL}")


def warning(msg):
    print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")


def success(msg):
    print(f"{Fore.LIGHTGREEN_EX}{msg}{Style.RESET_ALL}")
