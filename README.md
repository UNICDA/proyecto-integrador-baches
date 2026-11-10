# Sistema Móvil Inteligente para la Detección, Geolocalización, Reporte y Priorización de Baches en SDE 🛣️📍

Este proyecto propone una solución móvil y web para registrar, detectar, geolocalizar y priorizar baches en el municipio de Santo Domingo Este. Combina participación ciudadana, levantamientos técnicos en video y el uso de Inteligencia Artificial (IA) para mejorar la gestión del daño vial.

## 👥 Equipo de Proyecto (Grupo 6)
* **David de la Rosa** (2024-0145)
* **Samuel Roa** (2024-0102)
* **Anyelys Torres Castillo** (2024-0110)

---

## ✨ Características Principales

El sistema integra tres canales coordinados:

* **📱 Aplicación Móvil Ciudadana:** Permite a los ciudadanos registrarse, capturar fotografías de baches, ajustar la ubicación GPS en un mapa interactivo y guardar borradores cuando no hay conexión a internet.
* **🎥 Modo de Operador Técnico:** Permite al personal técnico grabar recorridos en video con telemetría GPS a lo largo de rutas definidas.
* **🧠 Inteligencia Artificial (Core):** Un modelo de visión artificial analiza las fotos ciudadanas y los fotogramas técnicos en segundo plano para proponer detecciones y severidades.
* **💻 Panel Web Administrativo:** Interfaz para que los revisores humanos confirmen, corrijan o fusionen los candidatos de la IA antes de publicarlos en un mapa ciudadano.

---

## 🛠️ Stack Tecnológico

El proyecto está diseñado bajo una arquitectura moderna, modular y escalable:

### Backend & Base de Datos
* **Framework:** Python con FastAPI
* **Base de Datos:** PostgreSQL con la extensión espacial PostGIS
* **Procesamiento Asíncrono:** Redis y Celery (para procesamiento de video e IA)
* **Inteligencia Artificial:** PyTorch, Ultralytics YOLO y OpenCV
* **Almacenamiento Multimedia:** Almacenamiento de objetos compatible con S3

### Frontend & Móvil
* **Aplicación Móvil:** React Native con Expo y TypeScript
* **Panel Web Administrativo:** React con TypeScript
* **Mapas:** React Native Maps (móvil) y Leaflet (web)

---

## 📁 Arquitectura del Backend

El esquema de base de datos consta de 14 tablas en Tercera Forma Normal (3FN), utilizando tipos de datos geoespaciales para la deduplicación espacial. El código del servidor sigue una arquitectura en capas:

```text
/app
 ├── api/          # Enrutadores y Endpoints de FastAPI (Controllers)
 ├── core/         # Configuración global, variables de entorno (.env) y seguridad
 ├── models/       # Modelos ORM (SQLAlchemy + GeoAlchemy2) conectados a PostgreSQL
 ├── schemas/      # Modelos Pydantic para validación de entrada/salida de datos
 ├── services/     # Lógica de negocio, consultas espaciales y reglas del dominio
 └── worker/       # Tareas asíncronas de Celery (Inferencia YOLO, extracción de fotogramas)
/alembic           # Sistema de migraciones versionadas de base de datos