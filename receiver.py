import socket
import json

def receive_exactly(connection, number_of_bytes):
    data = b""

    while len(data) < number_of_bytes:
        chunk = connection.recv(
            number_of_bytes - len(data)
        )

        if not chunk:
            raise ConnectionError("Connection closed early")

        data += chunk

    return data

HOST = "127.0.0.1"
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server.bind((HOST, PORT))
server.listen()

print(f"Waiting for connection on {HOST}:{PORT}...")

connection, address = server.accept()

print("Connected by: ", address)

length_bytes = receive_exactly(connection, 4)

# print("Raw length bytes:", length_bytes)

metadata_length = int.from_bytes(
    length_bytes,
    byteorder="big"
)

# print("Metadata length:", metadata_length)

metadata_bytes = receive_exactly(
    connection,
    metadata_length
)

# print("Raw metadata:", metadata_bytes)

metadata = json.loads(metadata_bytes.decode("utf-8"))

# print("Metadata:", metadata)

filename = metadata["filename"]
file_size = metadata["size"]

filename = "received_" + filename

with open(filename, "wb") as file:
    received = 0
    while received < file_size:
        remaining = file_size - received
        chunk = connection.recv(min(4096, remaining))

        if not chunk:
            raise ConnectionError("Connection closed before file was completely received")

        file.write(chunk)
        received += len(chunk)

print("File received successfully.")

# print("Received: ", data.decode())
# with open("received.txt", "wb") as file:
#     file.write(data)

connection.close()
server.close()