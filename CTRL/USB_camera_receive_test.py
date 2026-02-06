import socket
import struct
import cv2
import numpy as np
import threading

# Port numbers for each camera
PORTS = [22002, 22003]

def receive_stream(port, window_name):

# Set up the server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))  # Listen on all network interfaces
    server_socket.listen(1)
    print("Waiting for connection...")

    conn, addr = server_socket.accept()
    print(f"Connection from: {addr} on port: {port}")

    # Make a file-like object out of the connection
    connection = conn.makefile('rb')

    try:
        while True:
            # Read the length of the incoming image
            image_len_data = connection.read(struct.calcsize('<L'))
            if not image_len_data:
                break  # No data, exit loop

            image_len = struct.unpack('<L', image_len_data)[0]
            if image_len == 0:
                break  # Stop if sender signals the end

            # Read the image data
            image_data = connection.read(image_len)
            if not image_data:
                break

            # Convert the received bytes into a numpy array
            image_array = np.frombuffer(image_data, dtype=np.uint8)

            # Decode the image
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            # Show the received frame
            cv2.imshow(window_name, frame)

            # Exit when 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        connection.close()
        server_socket.close()
        cv2.destroyAllWindows()

# Start threads for both camera streams
camera1thread = threading.Thread(target=receive_stream, args=(22002, "Camera 1"))
camera2thread = threading.Thread(target=receive_stream, args=(22003, "Camera 2"))

camera1thread.start()
camera2thread.start()
