"""
Export N100 FastAPI OpenAPI specification and Postman collection.

Day 40 - N100 Financial Intelligence Platform
"""

import json
from pathlib import Path
import sys



PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

OPENAPI_PATH = DOCS_DIR / "openapi.json"
POSTMAN_PATH = DOCS_DIR / "postman_collection.json"


def build_postman_collection():
    """Build a Postman Collection v2.1 from FastAPI routes."""

    items = []

    for route in app.routes:

        if not hasattr(route, "methods"):
            continue

        if not hasattr(route, "path"):
            continue

        methods = sorted(route.methods)

        for method in methods:

            if method == "HEAD":
                continue

            path = route.path

            # Convert FastAPI path parameters:
            # {ticker} -> :ticker
            postman_path = path

            variables = []

            for parameter in route.param_convertors:
                postman_path = postman_path.replace(
                    "{" + parameter + "}",
                    ":" + parameter,
                )

                variables.append({
                    "key": parameter,
                    "value": "",
                })

            # Separate path segments.
            path_segments = [
                segment
                for segment in postman_path.strip("/").split("/")
                if segment
            ]

            request = {
                "name": f"{method} {route.path}",
                "request": {
                    "method": method,
                    "header": [],
                    "url": {
                        "raw": (
                            "http://127.0.0.1:8000"
                            + postman_path
                        ),
                        "protocol": "http",
                        "host": [
                            "127",
                            "0",
                            "0",
                            "1",
                        ],
                        "port": "8000",
                        "path": path_segments,
                    },
                },
                "response": [],
            }

            if variables:
                request["request"]["url"]["variable"] = variables

            items.append(request)

    return {
        "info": {
            "name": "N100 Financial Intelligence API",
            "description": (
                "Postman collection for the "
                "N100 Financial Intelligence Platform API."
            ),
            "schema": (
                "https://schema.getpostman.com/"
                "json/collection/v2.1.0/"
                "collection.json"
            ),
        },
        "variable": [
            {
                "key": "base_url",
                "value": "http://127.0.0.1:8000",
            }
        ],
        "item": items,
    }


def main():
    """Export API documentation files."""

    DOCS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Export FastAPI-generated OpenAPI specification.
    openapi_schema = app.openapi()

    OPENAPI_PATH.write_text(
        json.dumps(
            openapi_schema,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Export Postman collection.
    postman_collection = build_postman_collection()

    POSTMAN_PATH.write_text(
        json.dumps(
            postman_collection,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("API documentation export complete.")
    print(f"OpenAPI:  {OPENAPI_PATH}")
    print(f"Postman:  {POSTMAN_PATH}")
    print(
        f"OpenAPI routes: "
        f"{len(openapi_schema.get('paths', {}))}"
    )
    print(
        f"Postman requests: "
        f"{len(postman_collection['item'])}"
    )


if __name__ == "__main__":
    main()