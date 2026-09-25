#!/usr/bin/env python3
import os
import json
import time
import shutil
import hashlib
import subprocess
import base64

def run_bgp_lab():
    GREEN, RED, YELLOW, BOLD, CYAN, RESET = '\033[92m', '\033[91m', '\033[93m', '\033[1m', '\033[96m', '\033[0m'
    if os.name == 'nt': os.system("") # Enable ANSI for Windows

    print(f"\n{CYAN}{BOLD}{'='*65}\n        BGP Policy & Path Manipulation\n{'='*65}{RESET}")

    # 1. Container Engine Detection
    if shutil.which("podman"):
        engine, compose_cmd = "podman", ["podman", "compose"]
    elif shutil.which("docker"):
        # Check if docker compose v2 is available
        engine = "docker"
        compose_cmd = ["docker", "compose"] if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0 else ["docker-compose"]
    else:
        print(f"{RED}Error: Neither Podman nor Docker is installed or in PATH.{RESET}")
        return

    # 2. Get Student ID
    while True:
        student_id = input("Enter your 6-digit Student ID: ").strip()
        if len(student_id) == 6 and student_id.isdigit(): break
        print(f"{RED}Invalid format. Must be exactly 6 digits.{RESET}")

    # 3. Derive unique network parameters from ID
    ab, cd, ef = student_id[0:2], student_id[2:4], student_id[4:6]
    student_as = 65000 + int(ef)
    student_net = f"10.{ab}.{cd}.0/24"
    target_localpref = 100 + int(ef)
    target_med_link2 = 200 + int(ef)

    print(f"\n{YELLOW}Generating parametrized environment based on ID: {student_id}{RESET}")

    # 4. Generate configurations as strings (to inject without volume mounts)
    isp_a_conf = f"""!
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
"""
    isp_b_conf = f"""!
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
"""
    student_conf = "! Type your BGP configuration here\n!\n"

    # Helper function to create the shell command that builds configs inside the container
    def build_startup_cmd(conf_text):
        # Base64 encoding bypasses all shell escaping and newline headaches
        daemons_b64 = base64.b64encode(b"bgpd=yes\nzebra=yes\n").decode()
        vtysh_b64 = base64.b64encode(b"service integrated-vtysh-config\n").decode()
        conf_b64 = base64.b64encode(conf_text.encode('utf-8')).decode()
        
        return (
            f"/bin/sh -c \""
            f"echo '{daemons_b64}' | base64 -d > /etc/frr/daemons && "
            f"echo '{vtysh_b64}' | base64 -d > /etc/frr/vtysh.conf && "
            f"echo '{conf_b64}' | base64 -d > /etc/frr/frr.conf && "
            f"chown -R frr:frr /etc/frr && "
            f"/usr/lib/frr/docker-start\""
        )

    # 5. Generate Compose File
    # We use cap_add instead of privileged, and inject configs on boot to fix Rootless Podman limits
    compose_yaml = f"""
services:
  r_student:
    image: quay.io/frrouting/frr:8.4.1
    container_name: r_student
    cap_add: [NET_ADMIN, NET_RAW, SYS_ADMIN]
    command: {build_startup_cmd(student_conf)}
    networks:
      link1: {{ ipv4_address: 10.1.1.2 }}
      link2: {{ ipv4_address: 10.1.2.2 }}
      link3: {{ ipv4_address: 10.2.1.2 }}

  isp_a:
    image: quay.io/frrouting/frr:8.4.1
    container_name: isp_a
    cap_add: [NET_ADMIN, NET_RAW, SYS_ADMIN]
    command: {build_startup_cmd(isp_a_conf)}
    networks:
      link1: {{ ipv4_address: 10.1.1.1 }}
      link2: {{ ipv4_address: 10.1.2.1 }}

  isp_b:
    image: quay.io/frrouting/frr:8.4.1
    container_name: isp_b
    cap_add: [NET_ADMIN, NET_RAW, SYS_ADMIN]
    command: {build_startup_cmd(isp_b_conf)}
    networks:
      link3: {{ ipv4_address: 10.2.1.1 }}

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
    with open("compose.yaml", "w") as f: f.write(compose_yaml)

    # 6. Start the environment
    print(f"{CYAN}Booting router containers... (this may take a moment){RESET}")
    subprocess.run(compose_cmd + ["up", "-d"])

    # 7. Print Instructions
    print(f"\n{BOLD}LAB INSTRUCTIONS:{RESET}")
    print("You are the administrator of a new multi-homed AS. Configure your edge router (r_student).")
    print(f"\nTo test your configuration in real-time, open another terminal and run:")
    print(f"{BOLD}{CYAN}  {engine} exec -it r_student vtysh{RESET}\n")
    
    print(f"{BOLD}Your Assigned Variables:{RESET}")
    print(f"  - Your AS Number:     {YELLOW}{student_as}{RESET}")
    print(f"  - Your Network:       {YELLOW}{student_net}{RESET}\n")

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
        salt = "PA191-BGP_POLICY_LAB"
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
    subprocess.run([engine, "compose", "down", "-v", "--remove-orphans"])
    print("Done.")

if __name__ == '__main__':
    try:
        run_bgp_lab()
    except KeyboardInterrupt:
        print(f"\n{RED}Interrupt received. Tearing down environment...{RESET}")
        shutil.which("podman") and subprocess.run(["podman", "compose", "down", "-v", "--remove-orphans"])
        shutil.which("docker") and subprocess.run(["docker", "compose", "down", "-v", "--remove-orphans"])