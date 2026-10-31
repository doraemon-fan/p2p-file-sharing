"""
CLI wrapper for receiving files using the updated robust networking protocol.
Backwards compatible with the original receiver usage.
"""
import sys
import os
from backend.app.networking.receiver import FileReceiver

def main():
    host = "0.0.0.0"
    port = 5000
    downloads_dir = "downloads"

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        downloads_dir = sys.argv[2]

    os.makedirs(downloads_dir, exist_ok=True)
    receiver = FileReceiver(host=host, port=port, destination_dir=downloads_dir)
    print(f"Waiting for incoming connection on {host}:{port} (Saving to '{downloads_dir}')...")

    def on_progress(rec, total, speed):
        pct = (rec / total * 100) if total > 0 else 100
        speed_mb = speed / (1024 * 1024)
        print(f"\rReceiving: {pct:.1f}% ({rec}/{total} bytes) - {speed_mb:.2f} MB/s", end="", flush=True)

    try:
        result = receiver.accept_one_file(progress_callback=on_progress)
        print("\nFile received successfully!")
        print(f"Saved to: {result['file_path']}")
        print(f"SHA-256: {result['sha256']}")
        print(f"Duration: {result['duration_seconds']:.2f}s (Average: {result['average_speed_mbps']:.2f} MB/s)")
    except KeyboardInterrupt:
        print("\nReceiver stopped by user.")
    except Exception as e:
        print(f"\nReceive failed: {e}")
    finally:
        receiver.stop()

if __name__ == "__main__":
    main()