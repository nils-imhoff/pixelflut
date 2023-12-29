import asyncio
import socket
from PIL import Image

HOST = '151.217.15.90'  # Replace with the Pixelflut server IP
PORT = 1337                   # Replace with the Pixelflut server port
MAX_CONNECTIONS = 100          # Number of connections in the pool
IMAGE_PATH = '/home/nils/Bilder/pixel.png'  # Path to the image you want to send

def send_command(sock, command):
    """Send a command to the Pixelflut server."""
    sock.send(f"{command}\n".encode())

def pixel(sock, x, y, color):
    """Send a pixel command to the Pixelflut server."""
    send_command(sock, f"PX {x} {y} {color}")

async def get_canvas_size(sock):
    """Retrieve the canvas size from the Pixelflut server."""
    send_command(sock, "SIZE")
    response = await asyncio.to_thread(sock.recv, 1024)
    size_str = response.decode().strip()
    _, width, height = size_str.split()
    return int(width), int(height)

def prepare_image(image_path, width, height):
    """Load and resize image to fit the canvas."""
    image = Image.open(image_path)
    image = image.resize((width, height))
    return image

async def send_image_section(sock, image, start_row, end_row):
    """Send a section of the image."""
    width, height = image.size
    for y in range(start_row, end_row):
        for x in range(width):
            r, g, b = image.getpixel((x, y))
            pixel(sock, x, y, f'{r:02x}{g:02x}{b:02x}')
        await asyncio.sleep(0.01)  # Prevent overwhelming the server

async def create_connection():
    """Create a new connection to the server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    await asyncio.to_thread(sock.connect, (HOST, PORT))
    return sock

async def main():
    connections = [await create_connection() for _ in range(MAX_CONNECTIONS)]

    # Use the first connection to get the canvas size
    canvas_width, canvas_height = await get_canvas_size(connections[0])

    # Prepare the image
    image = prepare_image(IMAGE_PATH, canvas_width, canvas_height)

    # Divide the image and send in parallel
    height_per_connection = image.height // MAX_CONNECTIONS
    tasks = []
    for i, sock in enumerate(connections):
        start_row = i * height_per_connection
        end_row = (i + 1) * height_per_connection if i < MAX_CONNECTIONS - 1 else image.height
        task = asyncio.create_task(send_image_section(sock, image, start_row, end_row))
        tasks.append(task)

    await asyncio.gather(*tasks)

    # Close all connections
    for sock in connections:
        sock.close()

if __name__ == "__main__":
    asyncio.run(main())

