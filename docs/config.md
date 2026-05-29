# Environment Configuration

Documents every manual change made to this container outside of source code, and why each change was needed.

---

## 1. `~/.bashrc` additions

### 1a. `setup_isaaclab` function

```bash
setup_isaaclab() { … }
```

**Why:** Isaac Sim ships its own Python 3.11 and a large set of extension packages
(`isaacsim`, `omni`, `carb`, …) that live under `/home/isaac_sim/kit/` and are not
visible to the system Python 3.12.  Isaac Lab source packages (`isaaclab`,
`isaaclab_tasks`, etc.) are checked out as editable source under
`/home/isaac_sim/IsaacLab/source/` and are likewise invisible until explicitly added to
`PYTHONPATH`.

`setup_isaaclab` must be called once per terminal before running any Isaac Lab script.
It does four things:

| Action | Detail |
|---|---|
| `unset PYTHONPATH` | Clears ROS2 Python 3.12 paths that `~/.bashrc` sources automatically |
| Export `ISAAC_PATH`, `CARB_APP_PATH`, `EXP_PATH` | Required by `AppLauncher._resolve_experience_file()` — without these the launcher throws `KeyError: 'EXP_PATH'` |
| `source setup_python_env.sh` | Adds all Isaac Sim extension paths to `PYTHONPATH` and `LD_LIBRARY_PATH` |
| Add IsaacLab + robot\_lab source dirs to `PYTHONPATH` | Makes `isaaclab`, `isaaclab_tasks`, `robot_lab`, `unitree_rl_lab`, … importable (includes near-locomotion-quadruped paths) |
| Prepend `kit/python/bin` to `PATH` + alias `python`/`python3` | Routes both `python` and `python3` to Python 3.11.13 in Isaac Lab terminals |

**Usage:**
```bash
source ~/.bashrc   # or open a new terminal
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 --headless
```

### 1b. `unset PYTHONPATH` before ROS2 sourcing

```bash
unset PYTHONPATH
source /opt/ros/jazzy/setup.bash
```

**Why:** ROS2 Jazzy uses Python 3.12. Its `setup.bash` appends ROS package paths to
`PYTHONPATH`. If Isaac Sim's Python 3.11 paths were already in `PYTHONPATH` from a
previous session or shell, they would contaminate the ROS2 overlay. Unsetting first
guarantees each new terminal has a clean ROS2 Python environment.

---

## 2. `/usr/local/bin/python` symlink

```bash
sudo ln -sf /home/isaac_sim/kit/python/bin/python3.11 /usr/local/bin/python
```

**Why:** Ubuntu 24.04 ships only `python3` (Python 3.12); there is no bare `python`
command. Many scripts (including `robot_lab` training scripts) call `python` directly,
which produced `bash: python: command not found`.

The symlink makes `python` available system-wide and points it to Isaac Sim's Python
3.11. ROS2 tooling uses `python3` explicitly and is unaffected.

---

## 3. Packages installed into Isaac Sim Python 3.11

Installed via `--no-deps` to avoid re-downloading torch (Isaac Sim already bundles torch 2.7.0+cu128 at `exts/omni.isaac.ml_archive/pip_prebundle/`):

```bash
/home/isaac_sim/kit/python/bin/python3.11 -m pip install --no-deps \
  flatdict h5py numpy \
  rsl-rl-lib \
  tensordict pyvers cloudpickle importlib_metadata orjson \
  onnx onnxscript onnx_ir protobuf \
  GitPython gitdb smmap \
  torchvision pillow \
  packaging typing_extensions zipp
```

| Package | Why needed |
|---|---|
| `flatdict` | `isaaclab.sim.simulation_context` imports it at module load — without it `isaaclab_assets` fails to start |
| `h5py` + `numpy` | `isaaclab_tasks` HDF5 dataset handler |
| `rsl-rl-lib` | RSL-RL PPO library; `play.py` checks `metadata.version("rsl-rl-lib")` on startup |
| `tensordict` + `pyvers` + `cloudpickle` + `orjson` + `importlib_metadata` | `rsl_rl.algorithms.distillation` deps |
| `onnx` + `onnxscript` + `onnx_ir` + `protobuf` | Required for ONNX policy export |
| `GitPython` + `gitdb` + `smmap` | `rsl_rl.utils.logger` records git commit hash |
| `torchvision` + `pillow` | Declared `rsl-rl-lib` dep |
| `packaging` + `typing_extensions` + `zipp` | Leaf deps of the above |

> **Why `--no-deps`:** Without it, pip pulls torch 2.12.0 + ~1.5 GB of CUDA 13 libs.
> Isaac Sim's bundled torch 2.7.0+cu128 satisfies `rsl-rl-lib`'s `torch>=2.6.0`
> requirement and is already on `PYTHONPATH` via `setup_python_env.sh`.

---

## 3b. PyTorch venv (system Python 3.12, CUDA 12.8)

A separate venv at `/home/isaac_sim/torch-env` provides PyTorch for standalone scripts
that need CUDA but do not use Isaac Sim (e.g. model inspection, ONNX conversion, custom
eval scripts). It runs Python 3.12 and is completely separate from Isaac Sim's bundled
Python 3.11 environment.

**Created with:**

```bash
python3 -m venv /home/isaac_sim/torch-env
source /home/isaac_sim/torch-env/bin/activate
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
```

**Installed versions:**

| Package | Version |
|---|---|
| torch | 2.12.0.dev20260407+cu128 |
| torchvision | 0.27.0.dev20260407+cu128 |
| torchaudio | 2.11.0.dev20260407+cu128 |

CUDA 12.8, `torch.cuda.is_available()` → `True`.

**Activate when needed:**

```bash
source /home/isaac_sim/torch-env/bin/activate
```

> **Do not use for Isaac Lab training.** Isaac Sim's own Python 3.11 with its bundled
> torch 2.7.0+cu128 is used there via `setup_isaaclab`. This venv is for everything else.

---

## 4. `/home/isaac_sim/.cache` permissions

```bash
sudo chmod o+w /home/isaac_sim/.cache/
```

**Why:** The `.cache` directory was created by root during the Docker image build
(`drwxr-xr-x root root`). The `isaac_sim` user could not create subdirectories inside
it. Without this fix, Isaac Sim crashes immediately on startup with:

```
PermissionError: [Errno 13] Permission denied: '/home/isaac_sim/.cache/warp'
```

Adding world-write permission lets the `isaac_sim` user create the `warp/` kernel cache directory.

> **Note:** This is a one-time fix already applied to the current container. If the container
> is ever rebuilt from scratch, this command must be re-run before launching Isaac Sim.

---

## 5. `play.py` — `--load_actor_only` flag

**File:** `robot_lab/scripts/reinforcement_learning/rsl_rl/play.py`

**What was added:**

```python
# argparse
parser.add_argument("--load_actor_only", action="store_true", default=False, ...)

# runner.load call
load_cfg = {"actor": True, "critic": False, "optimizer": False, "iteration": False} if args_cli.load_actor_only else None
runner.load(resume_path, load_cfg=load_cfg)
```

**Why this flag exists — flat model on rough terrain task:**

The actor and critic are separate networks with separate input sizes:

| Network | Input (flat task) | Input (rough task) |
|---|---|---|
| Actor | 57 (base obs only) | 57 (base obs only) |
| Critic | 60 (base obs + 3 extras) | 247 (base obs + height scans + privileged state) |

The critic in rough terrain receives privileged observations — height scans, contact forces,
terrain geometry — that the flat terrain critic never saw. These are training-time extras fed
only to the critic so it can estimate value better; they are **never** seen by the actor and
are **never** present at deployment.

When you load a flat-trained checkpoint into the rough terrain task, `runner.load` tries to
restore both networks. The actor loads fine (same 57-input architecture). The critic fails
immediately with a `RuntimeError` because its saved weights have shape `[hidden, 60]` but the
rough terrain critic expects shape `[hidden, 247]`.

The fix is to skip the critic entirely on load. During `play` the critic is never called —
only the actor runs forward passes to produce actions. `--load_actor_only` passes
`load_cfg={"actor": True, "critic": False, "optimizer": False, "iteration": False}` to
`ppo.load`, which restores actor weights only and leaves the critic at its random
initialization (irrelevant since it is unused).

**Use whenever loading a flat-trained checkpoint into the rough terrain task:**

```bash
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --checkpoint /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_flat/<timestamp>/model_<N>.pt \
  --num_envs 1 --keyboard --real-time --load_actor_only
```

Not needed when loading a rough-trained checkpoint into the rough terrain task — critic
architectures match, so the normal load path works.

---

## 6. Test scripts

| File | Purpose |
|---|---|
| `/workspace/drop_sphere.py` | GUI test — opens Isaac Sim window, drops a sphere onto a ground plane |

Run with:
```bash
/home/isaac_sim/python.sh /workspace/drop_sphere.py    # GUI
```

`python.sh` sets up all Isaac Sim env vars internally so `setup_isaaclab` is not needed.
