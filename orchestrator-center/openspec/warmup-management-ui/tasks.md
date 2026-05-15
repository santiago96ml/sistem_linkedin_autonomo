# Tasks: Warmup Management System

## Bloque 1: Backend & Database (Current)
- [ ] Implementar modelos SQLAlchemy para `WarmupConfig` y `DailyActionLog`.
- [ ] Crear migración manual (script SQL) para actualizar `orchestrator.db`.
- [ ] Implementar endpoints `/warmup/*` en `main.py`.
- [ ] Crear el servicio `WarmupManager` en el backend para centralizar la lógica de límites.

## Bloque 2: Frontend "Warmup Lab"
- [ ] Crear el componente `WarmupView.tsx` en `frontend/src/components/views/`.
- [ ] Integrar `WarmupView` en el switch principal de `page.tsx`.
- [ ] Añadir pestaña "Warmup Lab" al Sidebar con icono de llama (Flame).
- [ ] Implementar el "Health Bar" dinámico y el progreso circular.

## Bloque 3: Inteligencia & Automatización
- [ ] Integrar `WarmupManager` en `orchestrator.py`.
- [ ] Implementar el "Circuit Breaker" de 150 acciones en `MissionRunner`.
- [ ] Crear el `NotificationSentry` para monitorizar VIPs.
- [ ] Desarrollar el `HigieneBot` (retiro de invitaciones antiguas).

## Bloque 4: Calibración LLM
- [ ] Ajustar el prompt de generación de comentarios para inyectar la `personality` y `niche`.
- [ ] Implementar respuestas automáticas para mensajes de networking.
