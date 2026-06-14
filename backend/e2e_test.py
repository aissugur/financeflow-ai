"""Quick end-to-end smoke test against the running server (port 8000).

Uses only the standard library so it runs with zero extra deps.
Run from the backend dir:  python e2e_test.py
"""
import json
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent


def _req(method, path, data=None, headers=None):
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers=headers or {}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get(path):
    return _req("GET", path)


def post_json(path, payload):
    body = json.dumps(payload).encode()
    return _req("POST", path, body, {"Content-Type": "application/json"})


def upload(file_path: Path):
    boundary = "----ffboundary1234"
    name = file_path.name
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode()
    body += file_path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return _req("POST", "/documents/upload", body, headers)


def main():
    print("HEALTH:", get("/health"))

    inv = upload(ROOT / "sample_docs" / "sample_invoice.txt")
    print(f"\nUPLOAD invoice -> id={inv['id']} status={inv['status']} "
          f"chunks={inv['num_chunks']}")

    a1 = post_json("/ask", {"document_id": inv["id"],
                            "question": "What is the total amount due?"})
    print(f"\nASK answerable -> abstained={a1['abstained']} mode={a1['mode']} "
          f"citations={len(a1['citations'])}")
    print("  answer:", a1["answer"])
    if a1["citations"]:
        c = a1["citations"][0]
        print(f"  top cite: {c['document_name']} chunk#{c['chunk_index']} "
              f"score={c['score']}")

    a2 = post_json("/ask", {"document_id": inv["id"],
                            "question": "What is the customer's social security number?"})
    print(f"\nASK should-abstain -> abstained={a2['abstained']}")
    print("  answer:", a2["answer"])

    docs = get("/documents")
    print(f"\nDOCUMENTS: {len(docs)} listed")

    hist = get(f"/history?document_id={inv['id']}")
    print(f"HISTORY: {len(hist)} entries for the invoice")

    ev = post_json("/evaluate", {})
    print("\nEVALUATE metrics:", json.dumps(ev["metrics"], indent=2))
    for c in ev["cases"]:
        flag = "PASS" if c["passed"] else "FAIL"
        print(f"  [{flag}] ({c['expectation']}) {c['question']}")
        print(f"         -> abstained={c['abstained']} cited={c['has_citation']}")

    # Clean up the doc created by this smoke test (keep DB tidy).
    _req("DELETE", f"/documents/{inv['id']}")
    print("\nDELETE invoice -> ok")
    print("\nALL CHECKS COMPLETE")


if __name__ == "__main__":
    main()
