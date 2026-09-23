#!/usr/bin/env python3
import os
import re
import json
import time
import shutil
import hashlib
import subprocess

def run_bgp_lab():
    # ANSI color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

    print("\n" + "="*65)
    print(f" {CYAN}{BOLD}        Advanced Routing Lab: BGP Policy & Path Manipulation{RESET}")
    print("="*65)

    # 1. Container Engine Detection
    if shutil.which("podman"):
        engine = "podman"
    elif shutil.which("docker"):
        engine = "docker"
    else:
        print(f"{RED}Error: Neither Podman nor Docker is installed or in PATH.{RESET}")
        return

    print(f"{GREEN}Detected container engine: {engine}{RESET}\n")

    # 2. Get Student ID
    while True:
        student_id = input("Enter your 6-digit Student ID: ").strip()
        if len(student_id) == 6 and student_id.isdigit():
            break
        print(f"{RED}Invalid format. Must be exactly 6 digits.{RESET}")

    # 3. Derive unique network parameters from ID
    ab = student_id[0:2]
    cd = student_id[2:4]
    ef = student_id[4:6]
    
    student_as = 65000 + int(ef)
    student_net = f"10.{ab}.{cd}.0/24"
    target_localpref = 100 + int(ef)
    target_med_link2 = 200 + int(ef)

    print(f"\n{YELLOW}Generating parametrized environment based on ID: {student_id}{RESET}")
    
    # 4. Generate Configuration Files
    configs_dir = os.path.join(os.getcwd(), "lab_configs")
    if os.path.exists(configs_dir):
        shutil.rmtree(configs_dir)

    for router in ["r_student", "isp_a", "isp_b"]:
        os.makedirs(os.path.join(configs_dir, router), exist_ok=True)
        with open(os.path.join(configs_dir, router, "daemons"), "w") as f:
            f.write("bgpd=yes\nzebra=yes\n")
        with open(os.path.join(configs_dir, router, "vtysh.conf"), "w") as f:
            f.write("service integrated-vtysh-config\n")

    # Generate ISP_A Config
    isp_a_conf = f"""!
router bgp 64501
 bgp router-id 1.1.1.1
 neighbor 10.1.1.2 remote-as {student_as}
 neighbor 10.1.2.2 remote-as {student_as}
 !
 address-family ipv4 unicast
  network 200.200.200.0/24
 exit-address-family
!
interface lo
 ip address 200.200.200.1/24
"""
    with open(os.path.join(configs_dir, "isp_a", "frr.conf"), "w") as f:
        f.write(isp_a_conf)

    # Generate ISP_B Config
    isp_b_conf = f"""!
router bgp 64502
 bgp router-id 2.2.2.2
 neighbor 10.2.1.2 remote-as {student_as}
 !
 address-family ipv4 unicast
  network 200.200.200.0/24
 exit-address-family
!
interface lo
 ip address 200.200.200.2/24
"""
    with open(os.path.join(configs_dir, "isp_b", "frr.conf"), "w") as f:
        f.write(isp_b_conf)

    with open(os.path.join(configs_dir, "r_student", "frr.conf"), "w") as f:
        f.write("! Type your BGP configuration here\n!\n")

    # 5. Generate Compose File (FIXED: Moved Docker's gateway to .254)
    compose_yaml = f"""
services:
  r_student:
    image: quay.io/frrouting/frr:8.4.1
    container_name: r_student
    privileged: true
    volumes:
      - ./lab_configs/r_student:/etc/frr:z
    networks:
      link1:
        ipv4_address: 10.1.1.2
      link2:
        ipv4_address: 10.1.2.2
      link3:
        ipv4_address: 10.2.1.2

  isp_a:
    image: quay.io/frrouting/frr:8.4.1
    container_name: isp_a
    privileged: true
    volumes:
      - ./lab_configs/isp_a:/etc/frr:z
    networks:
      link1:
        ipv4_address: 10.1.1.1
      link2:
        ipv4_address: 10.1.2.1

  isp_b:
    image: quay.io/frrouting/frr:8.4.1
    container_name: isp_b
    privileged: true
    volumes:
      - ./lab_configs/isp_b:/etc/frr:z
    networks:
      link3:
        ipv4_address: 10.2.1.1

networks:
  link1:
    ipam:
      config:
        - subnet: 10.1.1.0/24
          gateway: 10.1.1.254
  link2:
    ipam:
      config:
        - subnet: 10.1.2.0/24
          gateway: 10.1.2.254
  link3:
    ipam:
      config:
        - subnet: 10.2.1.0/24
          gateway: 10.2.1.254
"""
    with open("compose.yaml", "w") as f:
        f.write(compose_yaml)

    # 6. Start the environment (FIXED: Unmasked startup errors)
    print(f"{CYAN}Booting router containers... (this may take a while, up to 1-2 minutes){RESET}")
    subprocess.run([engine, "compose", "up", "-d"])

    # 7. Print Instructions
    print("\n" + "="*70)
    print(f"{BOLD}LAB INSTRUCTIONS:{RESET}")
    print("You are the administrator of a new multi-homed AS. You must configure ")
    print("your edge router (r_student) to meet the policy requirements below.")
    print(f"\nTo configure your router, edit this local file:")
    print(f"{BOLD}{YELLOW}  ./lab_configs/r_student/frr.conf{RESET}")
    print(f"\nTo test your configuration in real-time, open another terminal and run:")
    print(f"{BOLD}{CYAN}  {engine} exec -it r_student vtysh{RESET}\n")
    
    print(f"{BOLD}Your Assigned Variables:{RESET}")
    print(f"  - Your AS Number:     {YELLOW}{student_as}{RESET}")
    print(f"  - Your Network:       {YELLOW}{student_net}{RESET}\n")

    print(f"{BOLD}Tasks:{RESET}")
    print(f" 1. {BOLD}Peering:{RESET} Establish eBGP peerings with:")
    print(f"    - ISP_A (AS 64501) via Link 1 (10.1.1.1) and Link 2 (10.1.2.1)")
    print(f"    - ISP_B (AS 64502) via Link 3 (10.2.1.1)")
    print(f" 2. {BOLD}Origination:{RESET} Advertise {student_net} to all neighbors.")
    print(f" 3. {BOLD}Local Pref:{RESET} Force ALL outbound traffic for the internet")
    print(f"    (200.200.200.0/24) to go through ISP_A by setting a Local Preference")
    print(f"    of exactly {YELLOW}{target_localpref}{RESET} for routes received from ISP_A.")
    print(f" 4. {BOLD}MED:{RESET} ISP_A has two links. Tell ISP_A to prefer returning traffic")
    print(f"    via Link 1 by setting MED to {YELLOW}50{RESET} out Link 1, and {YELLOW}{target_med_link2}{RESET} out Link 2.")
    print(f" 5. {BOLD}AS Prepending:{RESET} You want ISP_B to strictly act as a backup.")
    print(f"    Prepend your AS exactly {YELLOW}3 times{RESET} to routes sent to ISP_B.")
    
    print("="*70 + "\n")
    input(f"{BOLD}Press [ENTER] when you are finished to grade the lab...{RESET}")

    # 8. Autograder Execution
    print("\n" + "="*65)
    print(f" {YELLOW}{BOLD}                  AUTOGRADER{RESET}")
    print("="*65)
    print(f"{CYAN}Waiting 5 seconds for BGP convergence...{RESET}")
    time.sleep(5)

    def get_bgp_json(container, prefix):
        cmd = [engine, "exec", container, "vtysh", "-c", f"show ip bgp {prefix} json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    lp_passed = False
    med_link1_passed = False
    med_link2_passed = False
    prepend_passed = False

    r_student_routes = get_bgp_json("r_student", "200.200.200.0/24")
    if r_student_routes and "paths" in r_student_routes:
        for path in r_student_routes["paths"]:
            if path.get("bestpath", {}).get("overall", False):
                nexthops = [nh.get("ip") for nh in path.get("nexthops", [])]
                if ("10.1.1.1" in nexthops or "10.1.2.1" in nexthops):
                    if path.get("locPrf") == target_localpref:
                        lp_passed = True

    isp_a_routes = get_bgp_json("isp_a", student_net)
    if isp_a_routes and "paths" in isp_a_routes:
        for path in isp_a_routes["paths"]:
            nh_ips = [nh.get("ip") for nh in path.get("nexthops", [])]
            metric = path.get("metric", 0)
            if "10.1.1.2" in nh_ips and metric == 50:
                med_link1_passed = True
            if "10.1.2.2" in nh_ips and metric == target_med_link2:
                med_link2_passed = True

    isp_b_routes = get_bgp_json("isp_b", student_net)
    if isp_b_routes and "paths" in isp_b_routes:
        for path in isp_b_routes["paths"]:
            aspath = path.get("aspath", {}).get("string", "")
            if aspath.count(str(student_as)) >= 4:
                prepend_passed = True

    passed = lp_passed and med_link1_passed and med_link2_passed and prepend_passed

    if passed:
        salt = "BGP_POLICY_LAB"
        token_hash = hashlib.sha256((salt + student_id).encode()).hexdigest()[:12]
        print(f"\n{GREEN}{BOLD}SUCCESS:{RESET} All BGP policies verified!")
        print(f"Submit this token to IS: {BOLD}{student_id}-{token_hash}{RESET}")
    else:
        print(f"\n{RED}{BOLD}FAILED:{RESET} Your network did not pass all tests:")
        if not lp_passed:
            print(f"- Local Preference check failed. Ensure the best path to 200.200.200.0/24 has LP {target_localpref}.")
        if not med_link1_passed:
            print("- MED check failed on Link 1. Ensure routes sent out 10.1.1.1 have MED 50.")
        if not med_link2_passed:
            print(f"- MED check failed on Link 2. Ensure routes sent out 10.1.2.1 have MED {target_med_link2}.")
        if not prepend_passed:
            print(f"- AS-Path check failed. Ensure you prepended AS {student_as} exactly 3 times out Link 3.")
            
    print("\n" + "="*65)
    print(f"{YELLOW}Tearing down environment...{RESET}")
    # FIXED: Added --remove-orphans and -v to ensure clean teardown, and unmasked errors.
    subprocess.run([engine, "compose", "down", "-v", "--remove-orphans"])
    print("Done.")

if __name__ == '__main__':
    try:
        run_bgp_lab()
    except KeyboardInterrupt:
        print(f"\n{RED}Interrupt received. Tearing down environment...{RESET}")
        shutil.which("podman") and subprocess.run(["podman", "compose", "down", "-v", "--remove-orphans"])
        shutil.which("docker") and subprocess.run(["docker", "compose", "down", "-v", "--remove-orphans"])