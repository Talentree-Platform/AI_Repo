import socket
import sys

def test_db_network_reachability(host: str, port: int = 1433):
    print(f"=== DB Connectivity Diagnosis Tool ===")
    print(f"Target Database Host: {host}")
    print(f"Target Database Port: {port}")
    print(f"Attempting to open raw TCP socket to target host...")
    
    try:
        # Create socket connection with a 5 second timeout
        s = socket.create_connection((host, port), timeout=5)
        s.close()
        print("\n[SUCCESS] Raw TCP Socket successfully connected to SQL Server!")
        print("This means your internet connection and local firewall are OPEN on port 1433.")
        print("If Python still fails, it could be a credentials or SSL/encryption settings mismatch.")
    except socket.timeout:
        print("\n[TIMEOUT ERROR] TCP Socket connection request timed out.")
        print("Diagnosis:")
        print("  1. Outbound traffic on port 1433 is likely BLOCKED by your internet provider, home router, or office firewall.")
        print("  2. Or, the MonsterASP database server is configured to drop external connection requests from your IP.")
    except Exception as e:
        print(f"\n[NETWORK ERROR] Could not establish connection: {e}")
        print("Diagnosis:")
        print("  Check your internet connection, or verify if the host name is spelled correctly.")

if __name__ == "__main__":
    host = "db52715.public.databaseasp.net"
    test_db_network_reachability(host)
