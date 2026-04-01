import requests
import json
import re
import sys
import time
from dotenv import load_dotenv
import os
from woocommerce import API

load_dotenv()
# =============================================================
#  CONFIG — completá con tus datos
# =============================================================

# --- Mercado Libre ---
ML_ACCESS_TOKEN  = os.getenv("ML_ACCESS_TOKEN")
ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN")
ML_CLIENT_ID     = os.getenv("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
ML_SITE_ID = os.getenv("ML_SITE_ID")

# --- Woocomerce ---
WC_URL             = os.getenv("WC_URL")
WC_CONSUMER_KEY    = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

# Categoría por defecto en WooCommerce
CATEGORIA_DEFAULT = "Productos"

# Pausa entre requests (segundos) para no exceder límites de la API de ML
PAUSA_SEGUNDOS = 0.5

# =============================================================
#  CLIENTE MERCADO LIBRE
# =============================================================

ML_API_BASE = "https://api.mercadolibre.com"
_ml_token   = ML_ACCESS_TOKEN   # Token activo en memoria


def renovar_token():
    global _ml_token
    if not ML_REFRESH_TOKEN or not ML_CLIENT_ID or not ML_CLIENT_SECRET:
        print("❌ Token expirado. Completá ML_REFRESH_TOKEN, ML_CLIENT_ID y ML_CLIENT_SECRET.")
        sys.exit(1)
    print("🔄 Token expirado, renovando automáticamente...")
    r = requests.post("https://api.mercadolibre.com/oauth/token", data={
        "grant_type":    "refresh_token",
        "client_id":     ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": ML_REFRESH_TOKEN,
    })
    data = r.json()
    if "access_token" in data:
        _ml_token = data["access_token"]
        with open("ml_token.txt", "w") as f:
            f.write(f"access_token={data['access_token']}\n")
            f.write(f"refresh_token={data.get('refresh_token', ML_REFRESH_TOKEN)}\n")
        print("✅ Token renovado y guardado en ml_token.txt\n")
    else:
        print(f"❌ No se pudo renovar el token: {data}")
        sys.exit(1)
 
 
def ml_get(endpoint, params=None):
    global _ml_token
    headers = {"Authorization": f"Bearer {_ml_token}"}
    url = f"{ML_API_BASE}{endpoint}"
    r = requests.get(url, headers=headers, params=params, timeout=20)
    if r.status_code == 401:
        renovar_token()
        headers = {"Authorization": f"Bearer {_ml_token}"}
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code == 401:
            print("❌ No se pudo autenticar con ML incluso después de renovar el token.")
            sys.exit(1)
    return r.json()
 
 
def obtener_user_id():
    data = ml_get("/users/me")
    uid = data.get("id")
    if not uid:
        print("❌ No se pudo obtener el usuario de ML. Verificá el Access Token.")
        sys.exit(1)
    print(f"✅ Conectado a Mercado Libre como: {data.get('nickname')} (ID: {uid})\n")
    return uid
 
 
def obtener_todos_los_items(user_id):
    items_ids = []
    offset    = 0
    limit     = 50
    print("🔍 Obteniendo lista de productos publicados en ML...")
    while True:
        data = ml_get(
            f"/users/{user_id}/items/search",
            params={"limit": limit, "offset": offset, "status": "active"}
        )
        resultados = data.get("results", [])
        items_ids.extend(resultados)
        total = data.get("paging", {}).get("total", 0)
        offset += limit
        print(f"   Obtenidos: {len(items_ids)} / {total}")
        if offset >= total or not resultados:
            break
        time.sleep(PAUSA_SEGUNDOS)
    print(f"\n📦 Total de productos en ML: {len(items_ids)}\n")
    return items_ids
 
 
def obtener_detalle_item(item_id):
    return ml_get(f"/items/{item_id}")
 
 
def obtener_descripcion(item_id):
    data = ml_get(f"/items/{item_id}/description")
    return data.get("plain_text", "") or data.get("text", "")
 
 
# =============================================================
#  CONTROL DE DUPLICADOS
# =============================================================
 
def obtener_skus_existentes(wcapi):
    """Obtiene todos los SKUs que ya existen en WooCommerce."""
    print("🔎 Verificando productos existentes en WooCommerce...")
    skus = set()
    page = 1
    while True:
        r = wcapi.get("products", params={"per_page": 100, "page": page})
        productos = r.json()
        if not productos:
            break
        for p in productos:
            sku = p.get("sku", "").strip()
            if sku:
                skus.add(sku)
        if len(productos) < 100:
            break
        page += 1
    print(f"   Productos ya existentes en WooCommerce: {len(skus)}\n")
    return skus
 
 
# =============================================================
#  TRANSFORMACIÓN ML → WooCommerce
# =============================================================
 
def construir_imagenes_wc(fotos_ml):
    imagenes = []
    for foto in fotos_ml:
        url = foto.get("secure_url") or foto.get("url", "")
        url = url.replace("-O.", "-F.").replace("-I.", "-F.")
        if url:
            imagenes.append({"src": url})
    return imagenes
 
 
def construir_atributos_wc(atributos_ml):
    attrs = []
    for attr in atributos_ml:
        nombre = attr.get("name", "").strip()
        valor  = attr.get("value_name", "")
        if nombre and valor:
            attrs.append({"name": nombre, "options": [valor], "visible": True})
    return attrs
 
 
def obtener_categoria(item):
    category_id = item.get("category_id", "")
    if not category_id:
        return []
    data = ml_get(f"/categories/{category_id}")
    nombre = data.get("name", "")
    return [{"name": nombre}] if nombre else []
 
 
def item_ml_a_producto_wc(item, descripcion=""):
    nombre    = item.get("title", "").strip()
    precio    = str(item.get("price", 0))
    stock     = item.get("available_quantity", 0)
    sku       = item.get("seller_sku") or item.get("id", "")
    atributos = item.get("attributes", [])
    fotos     = item.get("pictures", [])
    categoria = obtener_categoria(item)
    return {
        "name":           nombre,
        "type":           "simple",
        "status":         "publish",
        "regular_price":  precio,
        "manage_stock":   True,
        "stock_quantity": stock,
        "description":    descripcion,
        "sku":            str(sku),
        "categories":     categoria,
        "images":         construir_imagenes_wc(fotos),
        "attributes":     construir_atributos_wc(atributos),
    }
 
 
# =============================================================
#  CLIENTE WOOCOMMERCE
# =============================================================
 
def conectar_woocommerce():
    wcapi = API(
        url=WC_URL,
        consumer_key=WC_CONSUMER_KEY,
        consumer_secret=WC_CONSUMER_SECRET,
        version="wc/v3",
        timeout=30,
        verify_ssl=False
    )
    r = wcapi.get("products", params={"per_page": 1})
    if r.status_code != 200:
        print(f"❌ No se pudo conectar a WooCommerce: {r.status_code}")
        sys.exit(1)
    print("✅ Conexión a WooCommerce exitosa\n")
    return wcapi
 
 
# =============================================================
#  SCRIPT PRINCIPAL
# =============================================================
 
def main():
    print("=" * 55)
    print("  Importador Mercado Libre API → WooCommerce")
    print("  Productos Generales — shopofertas.com.ar")
    print("=" * 55 + "\n")
 
    wcapi   = conectar_woocommerce()
    user_id = obtener_user_id()
 
    # Obtener SKUs ya existentes para evitar duplicados
    skus_existentes = obtener_skus_existentes(wcapi)
 
    item_ids = obtener_todos_los_items(user_id)
 
    if not item_ids:
        print("⚠️  No se encontraron productos activos en ML.")
        return
 
    exitosos  = 0
    salteados = 0
    fallidos  = []
 
    for i, item_id in enumerate(item_ids, 1):
        print(f"[{i}/{len(item_ids)}] Procesando {item_id}...", end=" ")
 
        try:
            item        = obtener_detalle_item(item_id)
            sku         = str(item.get("seller_sku") or item.get("id", "")).strip()
 
            # Verificar si ya existe
            if sku in skus_existentes:
                print(f"⏭️  Ya existe (SKU: {sku}), salteando...")
                salteados += 1
                continue
 
            descripcion = obtener_descripcion(item_id)
            time.sleep(PAUSA_SEGUNDOS)
 
            payload = item_ml_a_producto_wc(item, descripcion)
 
            r = wcapi.post("products", payload)
 
            if r.status_code in (200, 201):
                wc_id = r.json().get("id")
                print(f"✅ WC ID: {wc_id} — {payload['name']}")
                exitosos += 1
                skus_existentes.add(sku)  # Agregar al set para evitar duplicados en esta misma ejecución
            else:
                error = r.json().get("message", r.text)
                print(f"❌ {error}")
                fallidos.append({"ml_id": item_id, "nombre": payload["name"], "error": error})
 
        except Exception as e:
            print(f"❌ Excepción: {e}")
            fallidos.append({"ml_id": item_id, "error": str(e)})
 
        time.sleep(PAUSA_SEGUNDOS)
 
    print("\n" + "=" * 55)
    print(f"  ✅ Subidos exitosamente: {exitosos}")
    print(f"  ⏭️  Salteados (ya existían): {salteados}")
    print(f"  ❌ Con error:               {len(fallidos)}")
 
    if fallidos:
        with open("errores_importacion.json", "w", encoding="utf-8") as f:
            json.dump(fallidos, f, ensure_ascii=False, indent=2)
        print("  📋 Errores guardados en: errores_importacion.json")
 
    print("=" * 55)
    input("\nPresioná Enter para cerrar...")
 
 
if __name__ == "__main__":
    main()
