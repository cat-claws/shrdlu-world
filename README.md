# SHRDLU Block World

Small standalone tabletop blocks-world simulator. It can run as a Python object,
a headless HTTP service, or a browser viewer for manual control.

## Run

```bash
cd ~/shrdlu-block-world

# Browser viewer at http://127.0.0.1:18123/
python3 -m shrdlu_blocks.simulator

# API only
python3 -m shrdlu_blocks.simulator --headless
```

Useful options:

- `--host HOST`
- `--port PORT`
- `--open-browser`

## Python API

```python
from shrdlu_blocks import ShrdluBlocksEnv

env = ShrdluBlocksEnv()
env.execute_action({"name": "move_grasper", "args": {"x": -0.1, "y": 0.4}})
env.execute_action({"name": "lower_grasper", "args": {}})
print(env.snapshot_text())
```

## HTTP API

- `GET /api/state`
- `POST /api/action`
- `POST /api/reset`

`POST /api/action` expects an action object:

```json
{
  "action": {
    "name": "move_grasper",
    "args": {"x": -0.1, "y": 0.4}
  }
}
```

Supported action names:

- `move_grasper` with `x` and `y`
- `lower_grasper`
- `raise_grasper`
- `close_grasper`
- `open_grasper`
- `highlight_object`
- `unhighlight_object`

## Configuration

```bash
export SHRDLU_SIMULATOR_HOST=0.0.0.0
export SHRDLU_SIMULATOR_PORT=18123
export SHRDLU_WEB_OPEN_BROWSER=1
```

For remote use, forward the viewer port and open `http://localhost:18123`:

```bash
ssh -L 18123:localhost:18123 user@remote-host
```

## Layout

- `shrdlu_blocks/simulator/`: environment, controller, scene model, and HTTP server
- `shrdlu_blocks/viewer/`: browser viewer and static assets
- `shrdlu_blocks/client.py`: small HTTP client for a running service
