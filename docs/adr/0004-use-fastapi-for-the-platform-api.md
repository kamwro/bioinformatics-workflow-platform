# ADR-0004: Use FastAPI for the platform API

## Status

Accepted

## Date

2026-05-09

## Context

The project needs a small API layer around workflow execution. The API should expose run metadata, run status, report locations, and possibly future actions such as triggering new workflow runs.

The main bioinformatics workflow will live in Nextflow. The API is a platform layer, not the workflow engine itself.

Python is a better fit than TypeScript for this part of the portfolio because Python is common in scientific and bioinformatics ecosystems.

## Decision

We will use **FastAPI** for the platform API.

FastAPI is not chosen because it is a bioinformatics standard. It is chosen because it is a lightweight, modern Python framework for API-first services, type hints, OpenAPI documentation, and integration with Python-based tooling.

## Alternatives considered

### Flask

Viable alternative. Flask is lightweight and widely used, especially historically in scientific Python projects. FastAPI is preferred here because of type hints, automatic OpenAPI documentation, and a more API-first developer experience.

### Django / Django REST Framework

Viable alternative for larger applications with admin panels, authentication, permissions, and complex business models. It is likely too heavy for this MVP.

### NestJS

Technically viable and familiar to the author, but rejected for the MVP because it would make the project look more like a TypeScript/web platform project and less like a Python-adjacent bioinformatics engineering project.

## Consequences

- The project demonstrates Python API development.
- OpenAPI documentation can be generated automatically.
- The backend remains focused on metadata and integration, while Nextflow handles workflow execution.
- If the project grows into a large internal platform, Django/DRF could be reconsidered.

## Sources

- FastAPI official documentation describes it as a modern Python framework for building APIs based on standard Python type hints: https://fastapi.tiangolo.com/
- Flask official documentation describes Flask as a lightweight WSGI web application framework: https://flask.palletsprojects.com/
- Django REST Framework official documentation describes DRF as a flexible toolkit for building Web APIs: https://www.django-rest-framework.org/
- Biopython describes Python tools for biological computation and bioinformatics: https://biopython.org/
