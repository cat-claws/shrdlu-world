"""Limited HTTP API server for a live SHRDLU blocks simulator."""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional, Type
from urllib.parse import urlparse

from shrdlu_blocks.simulator.env import ShrdluBlocksEnv

LOGGER = logging.getLogger(__name__)

DEFAULT_SIMULATOR_HOST = '0.0.0.0'
DEFAULT_SIMULATOR_PORT = 18123

__all__ = [
    'DEFAULT_SIMULATOR_HOST',
    'DEFAULT_SIMULATOR_PORT',
    'SimulatorRequestHandler',
    'SimulatorServer',
    'run_simulator_server',
]


class SimulatorServer:
    """Serve the standalone simulator through a deliberately small HTTP API."""

    def __init__(
        self,
        env: Optional[ShrdluBlocksEnv] = None,
        title: str = 'SHRDLU Blocks Simulator API',
        initial_output: str = 'Ready.',
    ):
        self.env = env or ShrdluBlocksEnv()
        self.title = title
        self.initial_output = initial_output
        self._lock = threading.RLock()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def serve(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        open_browser: Optional[bool] = None,
    ) -> None:
        """Start the simulator API server and block until interrupted."""
        server, url, actual_host, actual_port = self._make_server(host, port)
        self._announce_server(url, actual_host, actual_port)
        self._maybe_open_browser(url, open_browser)
        self._server = server
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nStopping simulator server.')
        finally:
            server.server_close()
            self._server = None

    def start_background(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        open_browser: Optional[bool] = None,
    ) -> str:
        """Start the simulator API server in a daemon thread and return its URL."""
        if self._server is not None:
            actual_host, actual_port = self._server.server_address[:2]
            display_host = '127.0.0.1' if actual_host == '0.0.0.0' else actual_host
            return 'http://%s:%d/' % (display_host, actual_port)
        server, url, actual_host, actual_port = self._make_server(host, port)
        self._announce_server(url, actual_host, actual_port)
        self._maybe_open_browser(url, open_browser)
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
        return url

    def stop(self) -> None:
        """Stop a background simulator API server."""
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None

    def state_payload(self, output: Optional[str] = None) -> Dict[str, object]:
        """Return the JSON state payload served by ``GET /api/state``."""
        with self._lock:
            return {
                'title': self.title,
                'output': output if output is not None else self.initial_output,
                'event_revision': self.env.event_revision,
                'event_log': self.env.event_log(),
                'snapshot': self.env.snapshot(),
                'snapshot_text': self.env.snapshot_text(),
                'action_help': self.env.action_help(),
            }

    def execute_action(self, action: Dict[str, object]) -> Dict[str, object]:
        """Execute one validated simulator action and return an updated payload."""
        with self._lock:
            try:
                result = self.env.execute_action(action)
                output = result if result is not None else 'OK'
                ok = True
            except Exception as exc:
                output = 'ERROR: %s' % exc
                ok = False
            payload = self.state_payload(output=str(output))
            payload['ok'] = ok
            return payload

    def reset(self) -> Dict[str, object]:
        """Reset the simulator and return an updated payload."""
        with self._lock:
            self.env.reset()
            payload = self.state_payload(output='Environment reset.')
            payload['ok'] = True
            return payload

    def _make_server(
        self,
        host: Optional[str],
        port: Optional[int],
    ):
        host = host or _env_first('SHRDLU_SIMULATOR_HOST', 'SHRDLU_WEB_HOST') or DEFAULT_SIMULATOR_HOST
        if port is None:
            port_text = (
                _env_first('SHRDLU_SIMULATOR_PORT', 'SHRDLU_WEB_PORT')
                or str(DEFAULT_SIMULATOR_PORT)
            )
            port = int(port_text)
        logging.getLogger('shrdlu_blocks.simulator.control').setLevel(logging.WARNING)

        simulator = self
        handler_base = self._handler_base_class()

        class Handler(handler_base):
            pass

        Handler.simulator = simulator

        server = ThreadingHTTPServer((host, int(port)), Handler)
        actual_host, actual_port = server.server_address[:2]
        display_host = '127.0.0.1' if actual_host == '0.0.0.0' else actual_host
        url = 'http://%s:%d/' % (display_host, actual_port)
        return server, url, actual_host, actual_port

    def _handler_base_class(self) -> Type['SimulatorRequestHandler']:
        return SimulatorRequestHandler

    def _announce_server(self, url: str, actual_host: str, actual_port: int) -> None:
        print('Serving %s at %s' % (self.title, url))
        if actual_host == '0.0.0.0':
            print('Port-forward target: 0.0.0.0:%d' % actual_port)

    def _maybe_open_browser(self, url: str, open_browser: Optional[bool]) -> None:
        del url, open_browser


class SimulatorRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the simulator API."""

    simulator: SimulatorServer

    def log_message(self, format: str, *args) -> None:
        LOGGER.info('%s - %s', self.address_string(), format % args)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == '/api/state':
            self._send_json(self.simulator.state_payload())
            return
        if path in ('', '/'):
            self._send_text(
                200,
                'SHRDLU Blocks simulator API\n'
                'GET /api/state\n'
                'POST /api/action\n'
                'POST /api/reset\n',
            )
            return
        self._send_text(404, 'Not found')

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json({'ok': False, 'output': 'ERROR: %s' % exc}, status=400)
            return
        if path == '/api/action':
            action = body.get('action')
            if not isinstance(action, dict):
                self._send_json({'ok': False, 'output': 'ERROR: action must be an object'}, status=400)
                return
            self._send_json(self.simulator.execute_action(action))
            return
        if path == '/api/reset':
            self._send_json(self.simulator.reset())
            return
        self._send_json({'ok': False, 'output': 'Not found'}, status=404)

    def _read_json_body(self) -> Dict[str, object]:
        length = int(self.headers.get('Content-Length', '0') or '0')
        raw = self.rfile.read(length) if length else b'{}'
        try:
            body = json.loads(raw.decode('utf-8') or '{}')
        except json.JSONDecodeError as exc:
            raise ValueError('request body must be JSON') from exc
        if not isinstance(body, dict):
            raise ValueError('request body must be a JSON object')
        return body

    def _send_json(self, payload: Dict[str, object], status: int = 200) -> None:
        data = json.dumps(payload, sort_keys=True).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, status: int, text: str) -> None:
        data = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_simulator_server(
    env: Optional[ShrdluBlocksEnv] = None,
    title: str = 'SHRDLU Blocks Simulator API',
    initial_output: str = 'Ready.',
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """Run a headless simulator service exposing only the limited action API."""
    SimulatorServer(
        env=env,
        title=title,
        initial_output=initial_output,
    ).serve(host=host, port=port)


def _env_first(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


if __name__ == '__main__':
    run_simulator_server(env=ShrdluBlocksEnv())
