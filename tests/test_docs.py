from fastapi.testclient import TestClient


def test_docs_served_with_theme_switch(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text
    assert "bioflowops-dark-theme" in response.text  # dark stylesheet injected
    assert "swagger-theme-toggle" in response.text  # light/dark switch button


def test_openapi_schema_still_available(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "BioFlowOps API"
