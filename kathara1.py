#!/usr/bin/env python3
import os
import sys
import json
import time
import shutil
import hashlib
import subprocess

def run_bgp_lab():
    # Enable ANSI escape sequences on Windows Command Prompt
    if os.name == 'nt':
        os.system("")

    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

    print("\n" + "="*65)
    print(f" {CYAN}{BOLD}        Advanced Routing Lab: BGP Policy & Path Manipulation{RESET}")
    print("="*65)

    # Safely resolve the Kathará executable on any OS (.exe, .bat, or linux binary)
    kathara_bin = shutil.which("kathara")
    if not kathara_bin:
        print(f"{RED}Error: Kathará is not installed or not in PATH.{RESET}")
        print("Install from: https://github.com/KatharaFramework/Kathara/releases")
        return

    # 1. Get Student ID
    while True:
        student_id = input("Enter your 6-digit Student ID: ").strip()
        if len(student_id) == 6 and student_id.isdigit():
            break
        print(f"{RED}Invalid format. Must be exactly 6 digits.{RESET}")

    # 2. Derive unique network parameters from ID
    ab, cd, ef = student_id[0:2], student_id[2:4], student_id[4:6]
    student_as = 65000 + int(ef)
    student_net = f"10.{ab}.{cd}.0/24"
    target_localpref = 100 + int(ef)
    target_med_link2 = 200 + int(ef)

    print(f"\n{YELLOW}Generating Kathará environment based on ID: {student_id}{RESET}")
    
    # 3. Generate Kathará Lab Directory
    lab_dir = os.path.join(os.getcwd(), "bgp_policy_lab")
    if os.path.exists(lab_dir):
        shutil.rmtree(lab_dir)
    os.makedirs(lab_dir)

    # Helper to write files with forced Unix line endings (\n) and correct OS paths
    def write_file(linux_path, content):
        # Convert "isp_a/etc/frr/daemons" into OS-safe path (e.g. "isp_a\etc\frr\daemons" on Win)
        safe_path_parts = linux_path.split('/')
        full_path = os.path.join(lab_dir, *safe_path_parts)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # newline='\n' is CRITICAL for Windows so containers don't choke on \r\n
        with open(full_path, "w", newline='\n', encoding="utf-8") as f:
            f.write(content)

    # Topology definition
    write_file("lab.conf", """LAB_NAME="BGP_Policy_Lab"
r_student[image]="kathara/frr"
r_student[0]="link1"
r_student[1]="link2"
r_student[2]="link3"

isp_a[image]="kathara/frr"
isp_a[0]="link1"
isp_a[1]="link2"

isp_b[image]="kathara/frr"
isp_b[0]="link3"
""")

    # ISP_A Configuration
    write_file("isp_a.startup", """ip addr add 10.1.1.1/24 dev eth0
ip addr add 10.1.2.1/24 dev eth1
chown -R frr:frr /etc/frr
/etc/init.d/frr start
""")
    write_file("isp_a/etc/frr/daemons", "bgpd=yes\nzebra=yes\n")
    write_file("isp_a/etc/frr/vtysh.conf", "service integrated-vtysh-config\n")
    write_file("isp_a/etc/frr/frr.conf", f"""!
router bgp 64501
 bgp router-id 1.1.1.1
 no bgp ebgp-requires-policy
 neighbor 10.1.1.2 remote-as {student_as}
 neighbor 10.1.2.2 remote-as {student_as}
 !
 address-family ipv4 unicast
  network 200.200.200.0/24
 exit-address-family
!
interface lo
 ip address 200.200.200.1/24
""")

    # ISP_B Configuration
    write_file("isp_b.startup", """ip addr add 10.2.1.1/24 dev eth0
chown -R frr:frr /etc/frr
/etc/init.d/frr start
""")
    write_file("isp_b/etc/frr/daemons", "bgpd=yes\nzebra=yes\n")
    write_file("isp_b/etc/frr/vtysh.conf", "service integrated-vtysh-config\n")
    write_file("isp_b/etc/frr/frr.conf", f"""!
router bgp 64502
 bgp router-id 2.2.2.2
 no bgp ebgp-requires-policy
 neighbor 10.2.1.2 remote-as {student_as}
 !
 address-family ipv4 unicast
  network 200.200.200.0/24
 exit-address-family
!
interface lo
 ip address 200.200.200.2/24
""")

    # r_student Configuration
    write_file("r_student.startup", """ip addr add 10.1.1.2/24 dev eth0
ip addr add 10.1.2.2/24 dev eth1
ip addr add 10.2.1.2/24 dev eth2
chown -R frr:frr /etc/frr
/etc/init.d/frr start
""")
    write_file("r_student/etc/frr/daemons", "bgpd=yes\nzebra=yes\n")
    write_file("r_student/etc/frr/vtysh.conf", "service integrated-vtysh-config\n")
    write_file("r_student/etc/frr/frr.conf", "! Type your BGP configuration here\n!\n")

    # 4. Start the environment
    print(f"{CYAN}Booting Kathará network scenario... (this may take a few moments){RESET}")
    subprocess.run([kathara_bin, "lstart", "--noterminals", "-d", lab_dir])

    # 5. Print Instructions
    print("\n" + "="*70)
    print(f"{BOLD}LAB INSTRUCTIONS:{RESET}")
    print("You are the administrator of a new multi-homed AS. You must configure ")
    print("your edge router (r_student) to meet the policy requirements below.")
    print(f"\nTo configure your router, open a new terminal and run:")
    print(f"{BOLD}{CYAN}  kathara connect -d bgp_policy_lab r_student{RESET}")
    print(f"Then type {BOLD}vtysh{RESET} to begin configuring.\n")
    
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

    # 6. Autograder Execution
    print("\n" + "="*65)
    print(f" {YELLOW}{BOLD}                  AUTOGRADER{RESET}")
    print("="*65)
    print(f"{CYAN}Waiting 5 seconds for BGP convergence...{RESET}")
    time.sleep(5)

    def get_bgp_json(container, prefix):
        cmd = [kathara_bin, "exec", "-d", lab_dir, container, "--", "vtysh", "-c", f"show ip bgp {prefix} json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    lp_passed = med_link1_passed = med_link2_passed = prepend_passed = False

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
        salt = "PA191-BGP_POLICY_LAB"
        token_hash = hashlib.sha256((salt + student_id).encode()).hexdigest()[:12]
        print(f"\n{GREEN}{BOLD}SUCCESS:{RESET} All BGP policies verified!")
        print(f"Submit this token to IS: {BOLD}{student_id}-{token_hash}{RESET}")
    else:
        print(f"\n{RED}{BOLD}FAILED:{RESET} Your network did not pass all tests:")
        if not lp_passed: print(f"- Local Preference check failed. Expected LP {target_localpref}.")
        if not med_link1_passed: print("- MED check failed on Link 1. Expected MED 50.")
        if not med_link2_passed: print(f"- MED check failed on Link 2. Expected MED {target_med_link2}.")
        if not prepend_passed: print(f"- AS-Path check failed. Ensure you prepended AS {student_as} exactly 3 times.")
            
    print("\n" + "="*65)
    print(f"{YELLOW}Tearing down environment...{RESET}")
    subprocess.run([kathara_bin, "lclean", "-d", lab_dir])
    print("Done.")

if __name__ == '__main__':
    try:
        run_bgp_lab()
    except KeyboardInterrupt:
        print("\n\033[91mInterrupt received. Tearing down environment...\033[0m")
        lab_dir = os.path.join(os.getcwd(), "bgp_policy_lab")
        kathara_bin = shutil.which("kathara")
        if kathara_bin:
            subprocess.run([kathara_bin, "lclean", "-d", lab_dir])