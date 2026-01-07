from fastapi.testclient import TestClient
from app.main import app


def demo():
    client = TestClient(app)
    payload = {
        "rating": 3,
        "feedback": "The product is decent but a bit slow to load pages and sometimes shows an error when applying filters."
    }
    resp = client.post("/reviews", json=payload)
    print("Status:", resp.status_code)
    print(resp.json())


if __name__ == "__main__":
    demo()
