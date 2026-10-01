# Seguridad V2.9 — controles 48 al 62

48. Validación de formularios en servidor.
49. No se confía solo en JavaScript.
50. Longitudes máximas de campos.
51. Validación/normalización de cédula, fechas, teléfono y opciones.
52. Fotos limitadas a 5 MB.
53. Solo formatos de imagen admitidos.
54. Validación por contenido real y Pillow.
55. Archivos de foto renombrados con UUID.
56. Fotos se decodifican/reconstruyen como JPEG, sin ejecución.
57. Fotos privadas requieren login y autorización sobre el miembro.
58. QR & LINK usa token criptográfico aleatorio.
59. Link público vence a los 30 días.
60. Administrador puede revocar y generar un link nuevo.
61. Enlaces sensibles futuros pueden ser de un solo uso; el QR general no lo es porque debe servir para múltiples solicitudes.
62. Solicitudes públicas permanecen en MemberRegistration y no crean Members hasta aprobación administrativa.
