
import base64
import json
import urllib.request
import tkinter as tk
from tkinter import filedialog

WEBHOOK_URL = "http://localhost:5678/webhook-test/vision-analysis"

root = tk.Tk()
root.withdraw()

image_path = filedialog.askopenfilename(
    title="Choisir une image du produit",
    filetypes=[
        ("Images", "*.png *.jpg *.jpeg *.webp"),
        ("Tous les fichiers", "*.*"),
    ],
)

if not image_path:
    print("Aucune image sélectionnée.")
    raise SystemExit(1)

description = input("Décris le dommage constaté : ").strip()

if not description:
    print("La description ne peut pas être vide.")
    raise SystemExit(1)

with open(image_path, "rb") as image_file:
    image_base64 = base64.b64encode(
        image_file.read()
    ).decode("utf-8")

payload = {
    "image_base64": image_base64,
    "customer_description": description,
}

request = urllib.request.Request(
    WEBHOOK_URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=180) as response:
        print("\nStatut HTTP :", response.status)
        print("Réponse de n8n :")
        print(json.dumps(
            json.loads(response.read().decode("utf-8")),
            indent=2,
            ensure_ascii=False,
        ))
except Exception as error:
    print("\nÉchec du test :", error)
