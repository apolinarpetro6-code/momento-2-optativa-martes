# Mtr Play — Núcleo de datos (E1)

Proyecto integrador — Ingeniería de Sistemas, UCC, 2026-II.
apolinar petro garces

## Archivos

- `datos_originales.csv` — recorte real de diciembre 2010 del dataset Online Retail (UCI), archivo de
  partida para E1. No está alterado.
- `mtr_play_e1.sqlite` — base de datos SQLite ya generada al ejecutar el notebook: 4 tablas
  (`clientes`, `productos`, `pedidos`, `lineas_pedido`) con las restricciones de integridad ya aplicadas
  (NOT NULL, UNIQUE, CHECK, FOREIGN KEY) y el índice `idx_lineas_stock_code`.
- `E1_evidencias.ipynb` — evidencia técnica de E1: perfilado del dataset, diseño del esquema, pruebas de
  rechazo de datos inválidos, consultas SQL, comparación de plan de consulta antes/después del índice,
  y demostración de transacción atómica al registrar un pedido.
- `E1_informe.pdf` — informe de E1 dirigido a lectura no técnica.

## Esquema de base de datos

```sql
clientes(customer_id INTEGER PRIMARY KEY, pais TEXT NOT NULL)

productos(stock_code TEXT PRIMARY KEY, descripcion TEXT NOT NULL)

pedidos(
  invoice_no TEXT PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES clientes(customer_id),
  fecha TEXT,
  es_cancelacion INTEGER CHECK (es_cancelacion IN (0,1))
)

lineas_pedido(
  id INTEGER PRIMARY KEY,
  invoice_no TEXT REFERENCES pedidos(invoice_no),
  stock_code TEXT REFERENCES productos(stock_code),
  cantidad INTEGER CHECK (cantidad <> 0),
  precio_unitario REAL CHECK (precio_unitario > 0),
  UNIQUE(invoice_no, stock_code, cantidad, precio_unitario)
)
```

## Próxima etapa (E2)

Construir un backend (FastAPI) sobre esta misma base SQLite que exponga los endpoints de registro de
pedidos (en transacción), consulta de historial por producto, y las 3 consultas de reporte ya validadas
en el notebook — sin alterar el esquema ni las restricciones ya probadas.

## E2 — Backend y pipeline

Instala las dependencias y arranca el backend desde la raíz del repositorio:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en `http://127.0.0.1:8000/docs`.
El backend usa `mtr_play_e1.sqlite`, activa las claves foráneas por conexión y conserva el esquema de E1.

Para cargar otro CSV con el mismo formato de `datos_originales.csv`:

```bash
python pipeline.py datos_originales.csv --db-path mtr_play_e1.sqlite
```

El pipeline descarta filas sin `CustomerID`, con `UnitPrice <= 0` o con datos numéricos inválidos,
captura duplicados exactos y muestra al final el total rechazado agrupado por motivo.

Las pruebas se ejecutan con:

```bash
pytest
```
