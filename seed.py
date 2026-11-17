from sqlalchemy import text
from app.core.database import engine

def run_seed():
    print("Iniciando la siembra (seed) de datos en los catálogos...")

    with engine.begin() as conn:
        # 1. Roles de Usuario
        print("- Insertando user_roles...")
        conn.execute(text("""
            INSERT INTO user_roles (code, name, description) VALUES
            ('CITIZEN', 'Ciudadano', 'Usuario de la app móvil que reporta baches'),
            ('TECHNICIAN', 'Técnico', 'Operador autorizado para grabar recorridos técnicos'),
            ('REVIEWER', 'Revisor', 'Personal del ayuntamiento que valida las detecciones de la IA'),
            ('ADMIN', 'Administrador', 'Control total del panel web y configuraciones')
            ON CONFLICT (code) DO NOTHING;
        """))

        # 2. Niveles de Severidad (Con pesos matemáticos y colores Hex)
        print("- Insertando severity_levels...")
        conn.execute(text("""
            INSERT INTO severity_levels (code, name, priority_weight, color_hex, min_area_threshold_pct) VALUES
            ('LOW', 'Baja', 1.00, '#22C55E', 0.00),
            ('MEDIUM', 'Media', 2.50, '#EAB308', 5.00),
            ('HIGH', 'Alta', 5.00, '#F97316', 15.00),
            ('CRITICAL', 'Crítica', 10.00, '#EF4444', 30.00)
            ON CONFLICT (code) DO NOTHING;
        """))

        # 3. Estados del Bache
        print("- Insertando pothole_statuses...")
        conn.execute(text("""
            INSERT INTO pothole_statuses (code, name, is_public_visible, description) VALUES
            ('AI_CANDIDATE', 'Candidato de IA', FALSE, 'Detección automática pendiente de revisión humana'),
            ('PUBLIC_CONFIRMED', 'Confirmado Público', TRUE, 'Bache validado y visible en el mapa ciudadano'),
            ('REJECTED', 'Rechazado', FALSE, 'Falso positivo descartado por el revisor'),
            ('MERGED', 'Fusionado', FALSE, 'Absorbido por otro bache debido a duplicidad espacial'),
            ('REPAIRED', 'Reparado', TRUE, 'Bache solucionado por obras públicas')
            ON CONFLICT (code) DO NOTHING;
        """))

        # 4. Estados de Procesamiento (Para Celery)
        print("- Insertando processing_statuses...")
        conn.execute(text("""
            INSERT INTO processing_statuses (code, name, is_final_state) VALUES
            ('RECEIVED', 'Recibido', FALSE),
            ('QUEUED_CELERY', 'En cola de procesamiento', FALSE),
            ('PROCESSING_AI', 'Procesando con IA', FALSE),
            ('COMPLETED', 'Completado', TRUE),
            ('FAILED', 'Error de procesamiento', TRUE)
            ON CONFLICT (code) DO NOTHING;
        """))

        # 5. Acciones de Revisión (Auditoría)
        print("- Insertando review_actions...")
        conn.execute(text("""
            INSERT INTO review_actions (code, name, description) VALUES
            ('CONFIRM', 'Confirmar Bache', 'Valida la detección de la IA sin cambios mayores'),
            ('OVERRIDE_SEVERITY', 'Corregir Severidad', 'El revisor modificó la gravedad sugerida por la IA'),
            ('MERGE_DUPLICATE', 'Fusionar Duplicado', 'Une este candidato con un bache existente cercano'),
            ('REJECT_FALSE_POSITIVE', 'Descartar Falso Positivo', 'Marca la predicción como error del modelo'),
            ('MARK_REPAIRED', 'Marcar como Reparado', 'Actualiza el estado tras intervención de brigada')
            ON CONFLICT (code) DO NOTHING;
        """))

        # 6. Rutas Viales (Motor Geoespacial Base)
        print("- Insertando road_routes...")
        conn.execute(text("""
            INSERT INTO road_routes (name, road_geometry, buffer_meters, priority_weight) VALUES
            ('Avenida España', ST_GeomFromText('MULTILINESTRING((-69.86603 18.47214, -69.86175 18.47353, -69.85587 18.47467, -69.84976 18.47545))', 4326), 15.00, 1.00),
            ('Avenida San Vicente de Paúl', ST_GeomFromText('MULTILINESTRING((-69.85583 18.47481, -69.85324 18.48123, -69.84958 18.48834, -69.84560 18.49445))', 4326), 15.00, 1.00),
            ('Avenida Charles de Gaulle', ST_GeomFromText('MULTILINESTRING((-69.84650 18.49520, -69.84020 18.50210, -69.83540 18.50980, -69.82910 18.51730))', 4326), 15.00, 1.00),
            ('Avenida Ecológica', ST_GeomFromText('MULTILINESTRING((-69.83561 18.49752, -69.82845 18.49523, -69.82012 18.49411, -69.81155 18.49380))', 4326), 15.00, 1.00)
            ON CONFLICT (name) DO NOTHING;
        """))

    print("¡Siembra de datos completada con éxito!")

if __name__ == "__main__":
    run_seed()