# Seguridad V2.9 — Controles 1–35

V2.9 aplica el primer bloque del checklist aprobado sin cambiar la estructura funcional de miembros/ministerios.

1. Argon2id para contraseñas nuevas y migración transparente de hashes anteriores al iniciar sesión.
2. Contraseñas nunca se almacenan en texto plano.
3. Política reforzada: mínimo 8 caracteres, letras+números y rechazo de claves comunes/inicial conocida.
4. HTTPS obligatorio en producción (redirección 308, compatible con proxy de Render/Hostinger).
5. HSTS en HTTPS de producción.
6. SECRET_KEY obligatoria por variable de entorno en producción.
7. DATABASE_URL obligatoria por variable de entorno en producción.
8. Debug desactivado.
9–10. Acceso SQL parametrizado para datos de usuario; SQL dinámico se limita a nombres/fragmentos internos controlados.
11. Autoescape de Jinja + CSP para reducir XSS.
12. CSRF obligatorio en POST/PUT/PATCH/DELETE.
13. CSP con default-src self, object-src none, base-uri self, frame-ancestors none y form-action self.
14–16. Cookie de sesión Secure (producción), HttpOnly y SameSite=Lax.
17. Cierre por 30 min de inactividad y máximo absoluto de 8 horas.
18. Logout destruye la sesión.
19. Login limpia/regenera la sesión.
20. Cambio/restablecimiento de contraseña incrementa SessionVersion e invalida sesiones anteriores.
21. Roles: Administrador, Pastor/a, Asistente Pastora, Líder Ministerio.
22. Autorización aplicada en servidor.
23. Administrador: acceso total.
24. Pastor/a: módulos aprobados.
25. Asistente Pastora: mismos módulos aprobados que Pastor/a.
26. Líder: limitado a su ministerio.
27–30. Ver/crear/editar/borrar sujetos a autorización y alcance.
31. Exportaciones sujetas a autorización del módulo/rol.
32. Protección IDOR mediante validación del miembro/ministerio contra el alcance del usuario.
33. Roles válidos se aceptan desde lista cerrada; cambios de privilegio son solo de Administrador.
34. Creación/edición/cambio de rol se registra en AuditLog.
35. Mínimo privilegio: usuarios no administradores solo acceden a módulos y datos autorizados.

## Compatibilidad
- Las contraseñas existentes con hash Werkzeug siguen funcionando; tras un login correcto se migran a Argon2id.
- Se agrega `Users.SessionVersion` mediante migración idempotente para cerrar sesiones anteriores tras cambios de contraseña.
- No se borran miembros, ministerios, historial ni datos existentes.
