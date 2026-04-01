# Importador Mercado Libre → WooCommerce

## 📑 Descripción
Script en Python que permite importar productos desde Mercado Libre hacia WooCommerce utilizando sus APIs oficiales.

El sistema automatiza todo el proceso incluyendo autenticación, transformación de datos y control de duplicados.

## ⚙️ Funcionalidades
- 🔐 Autenticación OAuth con Mercado Libre
- 🔄 Renovación automática de Access Token
- 📦 Obtención de todos los productos activos
- 🧠 Transformación de datos ML → WooCommerce
- 🖼 Importación de imágenes optimizadas
- 🏷 Conversión de atributos y categorías
- 🚫 Control de duplicados por SKU
- 📊 Reporte final de resultados
- 📝 Log de errores en archivo JSON

## 🛠 Tecnologías
- Python
- Requests
- WooCommerce API
- dotenv

## 📦 Requisitos
- Python 3.x
- Cuenta de Mercado Libre (API habilitada)
- WooCommerce con API REST activa

## 🔑 Variables de entorno (.env)
Crear un archivo `.env` con:
- ML_CLIENT_ID=
- ML_CLIENT_SECRET=
- ML_ACCESS_TOKEN=
- ML_REFRESH_TOKEN=
- ML_SITE_ID=

- WC_URL=
- WC_CONSUMER_KEY=
- WC_CONSUMER_SECRET=

## 🚀 Uso

### 1. Obtener token inicial
```bash
python obtener_token_ml.py
```
### 2. Ejecutar importador
```bash
python script.py
```

## Autor ✒️
**Lucas Barrera**
* [LinkedIn](https://www.linkedin.com/in/lucas-barrera-dev)
