import base64
import json
from pathlib import Path

IMAGE_PATH = Path(__file__).parent / "glasses.png"

image_base64 = base64.b64encode(
    IMAGE_PATH.read_bytes()
).decode("utf-8")

payload = {
    "image_base64": image_base64,
    "customer_description": (
        "The glasses arrived with a visible scratch "
        "on the left lens."
    )
}

Path("request.json").write_text(
    json.dumps(payload),
    encoding="utf-8"
)

print("Fichier request.json créé.")
