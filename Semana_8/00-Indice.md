# Semana 8 · API headless de cuestionarios + interfaz de gestión

Bitácora del equipo de agentes del laboratorio de la **semana 8 de DAE**, proyecto
`dae-s08-api-headless`.

## Qué se entrega

Una API REST de cuestionarios (exámenes, preguntas y opciones) con Django 5.2 + DRF, consumida de tres
maneras sin pantalla —el contrato OpenAPI, un cliente de consola y una frontera de agente de IA— **más**
una interfaz web de gestión para el profesorado.

## Índice

| Nota | Contenido |
|---|---|
| [[01-Auditoria-inicial]] | Qué se encontró al empezar, la línea base y el proyecto de referencia S07 |
| [[02-Equipo-de-agentes]] | Los 11 agentes, su prioridad y qué entregó cada uno |
| [[03-Requisitos-y-aceptacion]] | Requisitos desglosados y criterios de aceptación |
| [[04-Arquitectura-y-ADR]] | Las tres decisiones de arquitectura y su justificación |
| [[05-Modelos-y-datos]] | `Exam`, `Question`, `Choice`, reglas de negocio y datos de arranque |
| [[06-API-y-codigos-HTTP]] | Tabla de endpoints y matriz de códigos verificados |
| [[07-Interfaz-grafica]] | Decisiones de diseño, pantallas y cómo entrar |
| [[08-Seguridad]] | Qué se resolvió y qué sigue vigente |
| [[09-Pruebas-y-resultados]] | 365 pruebas en verde, qué cubre cada fichero y la matriz de códigos |
| [[10-Git-y-commits]] | Los commits reales de la entrega |
| [[11-Docker-y-CI]] | Por qué no se incorporaron |
| [[12-Limitaciones-y-pendientes]] | Lo que queda abierto y quién debería decidirlo |

## Documentos del repositorio

- `README.md` — cómo ejecutar el proyecto y **tabla de la API**.
- `docs/` — detalle: requisitos, trazabilidad, arquitectura, seguridad, revisión y ADR.
- `Semana_8/` — esta bitácora.

## Estado final verificado

- `python manage.py check` → sin problemas.
- `python manage.py test` → **`Ran 365 tests ... OK`** (punto de partida: 61 pruebas, 21 fallando).
- `requirements.txt` **intacto**: 4 dependencias, ninguna añadida.