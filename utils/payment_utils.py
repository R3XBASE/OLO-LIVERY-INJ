import uuid
import os

def generate_tx_id():
    return f"TX{uuid.uuid4().hex[:8].upper()}"

def get_qris_image(price: float):
    price_map = {
        5000: "qris/qris_5k.png",
        10000: "qris/qris_10k.png",
        20000: "qris/qris_20k.png",
        50000: "qris/qris_50k.png"
    }
    
    closest_price = min(price_map.keys(), key=lambda x: abs(x - price))
    image_path = price_map.get(closest_price)
    
    if image_path and os.path.exists(image_path):
        return image_path
    return None