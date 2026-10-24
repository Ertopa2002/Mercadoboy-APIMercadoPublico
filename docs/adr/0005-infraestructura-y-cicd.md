# 0005 – Terraform, GitHub Actions, us-east-1, ambientes dev y pilot

- Estado: aceptada
- Fecha: 2026-10-23

## Decisión
- Infraestructura como código con Terraform; estado en S3 con bloqueo.
- CI/CD con GitHub Actions (lint, tests y empaquetado en cada PR).
- Región us-east-1, cuenta vionexus-sandbox, recursos etiquetados `proyecto=mp-poc`.
- Ambientes `dev` y `pilot` en la misma cuenta, separados por prefijo.
- Acceso por IAM Identity Center (perfil SSO de la CLI).
