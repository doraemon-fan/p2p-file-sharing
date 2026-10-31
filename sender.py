import socket
import json
import os

HOST = "127.0.0.1"
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect((HOST, PORT))

file_path = "wwy.mkv"
file_size = os.path.getsize(file_path)

metadata = {
    "filename": os.path.basename(file_path),
    "size": file_size
}

metadata_bytes = json.dumps(metadata).encode("utf-8")

# print(metadata_bytes)

metadata_length = len(metadata_bytes)

# print("Metadata:", metadata)
# print("Metadata bytes:", metadata_bytes)
# print("Metadata length:", metadata_length)

length_bytes = metadata_length.to_bytes(4, byteorder="big")

client.sendall(length_bytes)
client.sendall(metadata_bytes)

with open(file_path, "rb") as file:
    while True:
        chunk = file.read(4096)
        if not chunk:
            break
        client.sendall(chunk)

print("File sent successfully.")

# with open("test.txt", "rb") as file:
#     data = file.read()

# client.sendall(data)
# client.sendall(b"Hello from Peer A!")

client.close()