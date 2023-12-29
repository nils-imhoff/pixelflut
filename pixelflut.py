import asyncio
import socket
import logging
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOST = '151.217.15.90'  # Replace with the Pixelflut server IP
PORT = 1337                   # Replace with the Pixelflut server port
MAX_CONNECTIONS = 10          # Number of parallel connections
IMAGE_PATH = '/home/nils/Bilder/pixel.png'  # Path to the image you want to send

def send_command(sock, command):
    """Send a command to the Pixelflut server."""
    try:
        sock.send(f"{command}\n".encode())
    except Exception as e:
        logging.error(f"Error sending command: {e}")

async def get_pixel_color(sock, x, y):
    """Retrieve the color of a specific pixel from the server."""
    try:
        send_command(sock, f'PX {x} {y}')
        response = await asyncio.to_thread(sock.recv, 1024)
        color = response.decode().strip().split(' ')[-1]
        return color
    except Exception as e:
        logging.error(f"Error getting pixel color: {e}")
        return None

async def update_pixel_if_changed(sock, x, y, new_color):
    """Update the pixel on the server if its color has changed."""
    current_color = await get_pixel_color(sock, x, y)
    if current_color and current_color != new_color:
        send_command(sock, f'PX {x} {y} {new_color}')

async def send_segment_if_changed(sock, image, bbox):
    """Send a segment of the image if pixels have changed."""
    x0, y0, x1, y1 = bbox
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = image.getpixel((x, y))
            new_color = f'{r:02x}{g:02x}{b:02x}'
            await update_pixel_if_changed(sock, x, y, new_color)
        await asyncio.sleep(0.01)

async def create_connection():
    """Create a new connection to the server."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        await asyncio.to_thread(sock.connect, (HOST, PORT))
        logging.info("Connected to server.")
        return sock
    except Exception as e:
        logging.error(f"Failed to connect to the server: {e}")
        return None

def prepare_image(image_path):
    """Load and prepare the image."""
    image = Image.open(image_path)
    image = image.convert('RGB')  # Ensure image is in RGB format
    return image

def divide_image(image, num_segments):
    """Divide the image into segments."""
    width, height = image.size
    segment_height = height // num_segments
    return [(0, i * segment_height, width, (i + 1) * segment_height) for i in range(num_segments)]

async def main():
    """Main function to coordinate sending the image."""
    image = prepare_image(IMAGE_PATH)
    connections = [await create_connection() for _ in range(MAX_CONNECTIONS)]
    connections = [conn for conn in connections if conn is not None]

    if not connections:
        logging.error("No connections could be established.")
        return

    image_segments = divide_image(image, len(connections))
    tasks = [asyncio.create_task(send_segment_if_changed(conn, image, bbox))
             for conn, bbox in zip(connections, image_segments)]

    await asyncio.gather(*tasks)

    for sock in connections:
        sock.close()

if __name__ == "__main__":
    asyncio.run(main())
