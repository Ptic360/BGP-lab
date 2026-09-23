#!/usr/bin/env python3
import sys
import shutil
import subprocess

def automate_bgp_lab():
    print("=== BGP Lab Auto-Solver ===")
    
    # 1. Get Student ID
    while True:
        student_id = input("Enter the 6-digit Student ID you used in the main lab script: ").strip()
        if len(student_id) == 6 and student_id.isdigit():
            break
        print("Invalid format. Must be exactly 6 digits.")

    # 2. Container Engine Detection
    if shutil.which("podman"):
        engine = "podman"
    elif shutil.which("docker"):
        engine = "docker"
    else:
        print("Error: Neither Podman nor Docker is installed or in PATH.")
        sys.exit(1)

    # 3. Derive unique network parameters
    ab = student_id[0:2]
    cd = student_id[2:4]
    ef = student_id[4:6]
    
    student_as = 65000 + int(ef)
    student_net = f"10.{ab}.{cd}.0/24"
    target_localpref = 100 + int(ef)
    target_med_link2 = 200 + int(ef)

    # 4. Generate the exact FRRouting Configuration
    vtysh_commands = f"""configure terminal
ip route {student_net} blackhole
router bgp {student_as}
 bgp router-id 10.1.1.2
 neighbor 10.1.1.1 remote-as 64501
 neighbor 10.1.2.1 remote-as 64501
 neighbor 10.2.1.1 remote-as 64502
 address-family ipv4 unicast
  network {student_net}
  neighbor 10.1.1.1 route-map RM-IN-ISP-A in
  neighbor 10.1.2.1 route-map RM-IN-ISP-A in
  neighbor 10.1.1.1 route-map RM-OUT-ISP-A-L1 out
  neighbor 10.1.2.1 route-map RM-OUT-ISP-A-L2 out
  neighbor 10.2.1.1 route-map RM-OUT-ISP-B out
 exit-address-family
exit
route-map RM-IN-ISP-A permit 10
 set local-preference {target_localpref}
exit
route-map RM-OUT-ISP-A-L1 permit 10
 set metric 50
exit
route-map RM-OUT-ISP-A-L2 permit 10
 set metric {target_med_link2}
exit
route-map RM-OUT-ISP-B permit 10
 set as-path prepend {student_as} {student_as} {student_as}
exit
exit
write memory
"""

    # 5. Inject configuration directly into the running r_student container
    print(f"\nPushing configuration for AS {student_as} to the r_student container...")
    
    try:
        # We use -i to pass our vtysh_commands string directly into standard input
        result = subprocess.run(
            [engine, "exec", "-i", "r_student", "vtysh"],
            input=vtysh_commands,
            text=True,
            capture_output=True
        )
        
        if result.returncode == 0:
            print("\n✅ Configuration applied successfully!")
            print("Switch back to the terminal running the main lab and press [ENTER] to run the autograder.")
        else:
            print(f"\n❌ Failed to apply configuration. Error output:\n{result.stderr}")
            
    except Exception as e:
        print(f"An error occurred while trying to communicate with the container: {e}")
        print("Make sure the original lab script is running and the containers are booted.")

if __name__ == '__main__':
    automate_bgp_lab()