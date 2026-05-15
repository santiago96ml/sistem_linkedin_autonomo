# Plan de Calentamiento y Estabilización de Cuentas LinkedIn

Este documento detalla la estrategia para resolver las restricciones de seguridad impuestas por LinkedIn en cuentas nuevas (como el caso de Morena Diaz) y mejorar la confiabilidad del orquestador mediante técnicas de antidetect y comportamiento humano.

## 1. Estado Original (Diagnóstico)

Hasta el momento, el sistema operaba bajo un modelo de **automatización directa**, lo que generaba las siguientes vulnerabilidades:

*   **Tipeo Robótico:** El texto se inyectaba con un retraso estático (`delay=30ms`), lo que permitía a los algoritmos de LinkedIn detectar fácilmente que no había un humano escribiendo.
*   **Identidad Técnica Compartida:** Sin un aislamiento estricto por IP (proxy) o huella digital (fingerprint), LinkedIn vinculaba cuentas nuevas con cuentas antiguas, penalizando a las primeras por falta de "historial de confianza".
*   **Ausencia de Límites Dinámicos:** No existía una distinción entre una cuenta establecida (Franco Robles) y una cuenta nueva, aplicando la misma intensidad de acciones a ambas.
*   **Detección de Interfaz Inconsistente:** El sistema a veces fallaba en detectar el botón "Comentar" real debido a la variabilidad del DOM de LinkedIn entre diferentes sesiones de usuario.

## 2. Objetivos de Mejora (Propuesta)

Para alcanzar un estado de "producción-ready" y evitar el *shadowban*, se implementarán los siguientes pilares:

### A. Humanización del Comportamiento (Human-like UI)
*   **Tipeo Errático:** Implementar una función de escritura que simule errores humanos, pausas para "pensar" y variaciones de velocidad entre pulsaciones de teclas.
*   **Navegación Fluida:** Añadir movimientos de ratón aleatorios y scroll natural antes de interactuar con elementos críticos.

### B. Sistema de Calentamiento (Warm-up Protocol)
*   **Fase de Sandbox:** Las cuentas nuevas tendrán un límite estricto de 5-10 acciones diarias durante los primeros 30 días.
*   **Incremento Gradual:** El sistema aumentará automáticamente los límites de acción a medida que la cuenta gane antigüedad.
*   **Modo Enfriamiento:** Capacidad de poner una cuenta en "reposo" total si se detectan señales de advertencia o bloqueos temporales.

### C. Aislamiento Técnico Estricto
*   **Proxies Dedicados:** Asegurar que cada cuenta use un Proxy Residencial único configurado en la base de datos.
*   **Fingerprint Isolation:** Refinar la configuración de Playwright para que cada sesión de navegador parezca un dispositivo distinto.

## 3. Implementación y Resultados Esperados

### Cambios en el Backend:
*   **`models.py`**: Adición de campos `is_warming_up`, `trust_score` y `last_action_at`.
*   **`orchestrator.py`**: Refactorización del método de envío de comentarios para usar la nueva lógica de escritura humana.
*   **`main.py`**: Lógica de control para prevenir el exceso de misiones en cuentas sensibles.

### Resultados Esperados:
1.  **Eliminación del error `COMMENT_SUBMIT_FAILED`** en cuentas nuevas al no activar los motores de spam de texto.
2.  **Escalabilidad Segura:** Posibilidad de gestionar 10+ cuentas desde el mismo servidor sin riesgo de baneo masivo.
3.  **Autonomía Inteligente:** El sistema detectará si una cuenta está "caliente" o "fría" y ajustará su comportamiento automáticamente.

---
*Documento creado el 30 de abril de 2026 para el Proyecto LinkedIn Orchestrator.*
