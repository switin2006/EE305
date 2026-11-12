import json
import math
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from transient_solver import simulate_transient

STATIC_DIR = Path(__file__).resolve().parent / "static"
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def _parse_finite(payload, key):
    if key not in payload:
        raise ValueError(f"Missing parameter '{key}'.")
    try:
        val = float(payload[key])
    except (TypeError, ValueError):
        raise ValueError(f"Parameter '{key}' must be a valid number.")
    if not math.isfinite(val):
        raise ValueError(f"Parameter '{key}' must be finite.")
    return val


class PortalHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        rel = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
        if "/" in rel or "\\" in rel or ".." in rel:
            self.send_error(404)
            return

        target = STATIC_DIR / rel
        if not target.is_file():
            self.send_error(404)
            return

        content_type = MIME_TYPES.get(target.suffix.lower(), "application/octet-stream")
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/simulate":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))

            V0 = _parse_finite(payload, "V0")
            Rg = _parse_finite(payload, "Rg")
            l = _parse_finite(payload, "l")
            u = _parse_finite(payload, "u")
            R0 = _parse_finite(payload, "R0")
            X0 = _parse_finite(payload, "X0")
            t_max_T = _parse_finite(payload, "t_max_T")
            load_type = payload.get("load_type", "inductive")

            if t_max_T > 200:
                raise ValueError("Time span (multiples of T) must be <= 200.")

            LL = _parse_finite(payload, "LL") if load_type == "inductive" else None
            CL = _parse_finite(payload, "CL") if load_type == "capacitive" else None

            points_per_T = 500 if t_max_T <= 20 else max(80, int(10000 / t_max_T))
            t_norm, V_input, params = simulate_transient(
                V0=V0,
                Rg=Rg,
                l=l,
                u=u,
                R0=R0,
                X0=X0,
                load_type=load_type,
                LL=LL,
                CL=CL,
                t_max_T=t_max_T,
                points_per_T=points_per_T,
            )

            self._send_json(
                200,
                {
                    "t_norm": t_norm.tolist(),
                    "V_input": V_input.tolist(),
                    "params": params,
                },
            )
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"Server error: {exc}"})


def main():
    is_cloud = "PORT" in os.environ
    host = os.environ.get("HOST", "0.0.0.0" if is_cloud else "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), PortalHandler)
    url = f"http://{host}:{port}"
    print(f"EE305 Project 9 Portal running at {url}")
    if not is_cloud:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
