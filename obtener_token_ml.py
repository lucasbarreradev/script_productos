from dotenv import load_dotenv
import os

import requests

load_dotenv()

# =============================================================
#  COMPLETÁ CON TUS DATOS
# =============================================================
ML_CLIENT_ID = os.getenv("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
CODE = input("Pegá el CODE de la URL: ").strip()   # El code que copiaste de la URL
WC_URL = os.getenv("WC_URL")
# =============================================================

r = requests.post(
    "https://api.mercadolibre.com/oauth/token",
    headers={
        "accept":       "application/json",
        "content-type": "application/x-www-form-urlencoded",
    },
    data={
        "grant_type":   "authorization_code",
        "client_id":    ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code":          CODE,
        "redirect_uri":  WC_URL,
    }
)

data = r.json()

if "access_token" in data:
    print("\n✅ Token obtenido exitosamente!\n")
    print(f"  ACCESS TOKEN:  {data['access_token']}")
    print(f"  REFRESH TOKEN: {data.get('refresh_token', 'N/A')}")
    print(f"  Expira en:     {data.get('expires_in', '?')} segundos (~3 horas)\n")
    print("👉 Copiá el ACCESS TOKEN y pegalo en ML_ACCESS_TOKEN del script principal.")
    print("👉 Copiá el REFRESH TOKEN y pegalo en ML_REFRESH_TOKEN para renovación automática.")

    # Guardar en archivo para no perderlos
    with open("ml_token.txt", "w") as f:
        f.write(f"access_token={data['access_token']}\n")
        f.write(f"refresh_token={data.get('refresh_token', '')}\n")
    print("\n💾 Tokens guardados en ml_token.txt")
else:
    print("\n❌ Error al obtener el token:")
    print(data)