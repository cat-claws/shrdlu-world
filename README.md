# SHRDLU Block World

This is the standalone tabletop blocks-world simulator package. It can run
in-process through a Python API, as a headless HTTP service, or with the browser
viewer for manual control and visual state updates.

## Install

From this directory:

```bash
python3 -m pip install -e .
```

The installable distribution is named `shrdlu-block-world`. The Python import
package is still named `shrdlu_blocks`:

```bash
python3 -m pip install "shrdlu-block-world @ file:///path/to/shrdlu-block-world"
```

The simulator package has no third-party, OpenAI, or agent dependency.

## In-Process API

```python
from shrdlu_blocks import ShrdluBlocksEnv

env = ShrdluBlocksEnv()
env.execute_action({"name": "move_grasper", "args": {"x": -0.1, "y": 0.4}})
env.execute_action({"name": "lower_grasper", "args": {}})
print(env.snapshot_text())
```

## Headless HTTP Service

```bash
python3 -m shrdlu_blocks.simulator --headless
```

This starts the simulator API without a viewer.

## Browser Viewer

```bash
python3 -m shrdlu_blocks.simulator
```

The viewer serves on `0.0.0.0:8000` by default. It shows the simulated state,
event log, manual grasper controls, explicit `x/y` move inputs, and object
selection/highlighting. It does not include an agent or command text box.

## Limited HTTP API

Both standalone modes expose:

- `GET /api/state`
- `POST /api/action`
- `POST /api/reset`

Allowed actions:

- `move_grasper` with `x` and `y`
- `lower_grasper`
- `raise_grasper`
- `close_grasper`
- `open_grasper`
- `highlight_object`
- `unhighlight_object`

## Port Forwarding

```bash
ssh -L 8000:localhost:8000 user@remote-host
```

Then open:

```text
http://localhost:8000
```

## Environment

```bash
export SHRDLU_SIMULATOR_HOST=0.0.0.0
export SHRDLU_SIMULATOR_PORT=8000
export SHRDLU_WEB_OPEN_BROWSER=0
```

## Project Structure

- `shrdlu_blocks/simulator/`: environment, controller internals, scene model, and HTTP API server
- `shrdlu_blocks/viewer/`: browser viewer assets and static UI server extension
- `shrdlu_blocks/client.py`: small HTTP client for a running simulator service
