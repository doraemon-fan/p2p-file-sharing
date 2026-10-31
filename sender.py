"""
CLI wrapper for sending files using the updated robust networking protocol.
Backwards compatible with the original sender usage.
"""
import sys
import os
from backend.app.networking.sender import FileSender

def main():
    host = "127.0.0.1"
    port = 5000
    file_path = "test.txt"

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    if len(sys.argv) > 2:
        host = sys.argv[2]
    if len(sys.argv) > 3:
        port = int(sys.argv[3])

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return

    print(f"Sending '{file_path}' ({os.path.getsize(file_path)} bytes) to {host}:{port}...")

    def on_progress(sent, total, speed):
        pct = (sent / total * 100) if total > 0 else 100
        speed_mb = speed / (1024 * 1024)
        print(f"\rProgress: {pct:.1f}% ({sent}/{total} bytes) - {speed_mb:.2f} MB/s", end="", flush=True)

    sender = FileSender(host=host, port=port)
    try:
        result = sender.send_file(file_path, progress_callback=on_progress)
        print("\nFile sent successfully!")
        print(f"SHA-256: {result['sha256']}")
        print(f"Duration: {result['duration_seconds']:.2f}s (Average: {result['average_speed_mbps']:.2f} MB/s)")
    except Exception as e:
        print(f"\nTransfer failed: {e}")

if __name__ == "__main__":
    main()