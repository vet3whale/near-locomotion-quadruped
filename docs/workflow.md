# B2W Robot Training Workflow

Train a locomotion policy in Isaac Lab (robot_lab), export it to ONNX, visualise it in Gazebo (b2w_ws), and optionally run autonomous goal navigation with rl_nav_controller.

---

## Step 1 — Train in Isaac Lab

Open a terminal and set up the Isaac Lab Python environment first.

```bash
source ~/.bashrc        # if in a fresh terminal
conda deactivate
setup_isaaclab
```

> **What `setup_isaaclab` does:** it is a shell function in `~/.bashrc` that runs
> `/home/isaac_sim/setup_python_env.sh` with `SCRIPT_DIR=/home/isaac_sim`, which adds the
> Isaac Sim and Isaac Lab package paths to `PYTHONPATH` so that `isaacsim` and `isaaclab`
> are importable. It is a function (not run automatically) because those paths conflict with
> ROS2's Python 3.12 — `~/.bashrc` does `unset PYTHONPATH` on startup to keep ROS2 clean,
> and `setup_isaaclab` restores them only in terminals where Isaac Lab scripts are needed.

### Fresh training (20 000 iterations default)

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless
```

### Resume from the latest checkpoint

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless \
  --resume
```

### Resume from a specific run

```bash
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless \
  --resume \
  --load_run 2026-05-24_05-47-04
```

Checkpoints are saved to:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/
```

> **Minimum iterations before the policy is usable:** ~3000–5000.
> The config default is 20 000 (`max_iterations` in `agents/rsl_rl_ppo_cfg.py`).
> Do **not** pass `--max_iterations 500` — that was what caused the erratic motion.

### Training configuration

| File | Key parameters |
|---|---|
| `agents/rsl_rl_ppo_cfg.py` | `max_iterations=20000`, `num_steps_per_env=24`, `save_interval=100` |
| `config/wheeled/unitree_b2w/rough_env_cfg.py` | Action scales (hip×0.125, leg×0.25, wheel×5.0), obs layout |

Training saves a checkpoint every 100 iterations. Ctrl+C is safe to interrupt between saves.
If the machine goes to sleep, training pauses and resumes on wake (the process stays alive).

---

## Step 1b — Watch the Robot Walk in Isaac Sim

Use `play.py` to load a checkpoint and visualise the robot in the Isaac Sim GUI. With `--keyboard` you steer it interactively; without it the environment sends random velocity commands automatically.

> **Minimum iterations before the robot walks:** ~3 000–5 000. At 499 iterations the policy is random — the robot collapses immediately. Train for at least 3 000 iterations before trying this step.

### Check how many iterations you have

```bash
ls /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/
# look for model_<N>.pt — the highest N is the last saved iteration
```


### Run play.py with keyboard control

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --load_run 2026-05-24_05-47-04 \
  --num_envs 1 \
  --keyboard
```

> Remove `--load_run` to auto-load the most recent run, or omit `--num_envs 1` to spawn multiple parallel environments (no keyboard in that case).

### Keyboard controls

| Key | Action |
|---|---|
| Arrow Up / Numpad 8 | Forward |
| Arrow Down / Numpad 2 | Backward |
| Arrow Left / Numpad 4 | Strafe left |
| Arrow Right / Numpad 6 | Strafe right |
| Z / Numpad 7 | Rotate left |
| X / Numpad 9 | Rotate right |
| L | Reset velocity to zero |

Without `--keyboard` the environment cycles through random velocity commands automatically — useful for a quick visual sanity check without touching the keyboard.

---

## Step 2 — Export to ONNX

`play.py` auto-exports `policy.onnx` into an `exported/` subfolder next to the loaded checkpoint.

> **Requires the Isaac Lab environment.** Run this in the same terminal setup as Step 1:
> ```bash
> conda deactivate
> setup_isaaclab
> ```

```bash
# Export from the latest checkpoint of the most recent run
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless

# Export from a specific run
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless \
  --load_run 2026-05-24_05-47-04
```

The exported policy will be at:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/exported/policy.onnx
```

---

## Step 3 — Sim2Sim in MuJoCo

Run the exported ONNX policy against the MuJoCo simulator over DDS on loopback.
No physical robot or gamepad required — control is via keyboard.

> **Full details** (failure modes, hardware checklist, gamepad alternative): see
> [`docs/mujoco_sim2sim.md`](mujoco_sim2sim.md).

### One-time setup (do once per machine)

```bash
# System packages
sudo apt update
sudo apt install -y libyaml-cpp-dev libspdlog-dev libboost-all-dev
```

> **`libglfw3-dev` may not be in the apt repos** on Ubuntu 24.04. If the `apt install` fails,
> build GLFW from source:
> ```bash
> sudo apt install -y cmake xorg-dev
> git clone https://github.com/glfw/glfw.git /tmp/glfw
> cmake -S /tmp/glfw -B /tmp/glfw/build \
>   -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local \
>   -DBUILD_SHARED_LIBS=ON -DGLFW_BUILD_DOCS=OFF -DGLFW_BUILD_TESTS=OFF -DGLFW_BUILD_EXAMPLES=OFF
> sudo cmake --build /tmp/glfw/build --target install -j$(nproc)
> ```

```bash
# unitree_sdk2 - use sudo if restricted permissions
cd /opt/unitree_robotics
git clone https://github.com/unitreerobotics/unitree_sdk2.git
cd unitree_sdk2 && mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/opt/unitree_robotics
sudo make install

# MuJoCo 3.3.6
mkdir -p ~/.mujoco && cd ~/.mujoco
wget https://github.com/google-deepmind/mujoco/releases/download/3.3.6/mujoco-3.3.6-linux-x86_64.tar.gz
tar -xzf mujoco-3.3.6-linux-x86_64.tar.gz

# Symlink MuJoCo into the simulate source tree
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate
ln -s ~/.mujoco/mujoco-3.3.6 mujoco

# Create the missing .so symlink for ONNX Runtime (linker needs unversioned name)
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/thirdparty/onnxruntime-linux-x64-1.22.0/lib
ln -s libonnxruntime.so.1.22.0 libonnxruntime.so
```

### Build (do once, redo after code changes)

```bash
# Build the MuJoCo simulator bridge
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate
mkdir -p build && cd build
cmake .. && make -j$(nproc)

# Build the B2W controller
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/robots/b2w
mkdir -p build && cd build
cmake .. && make -j$(nproc)
```

### Configure (before each session)

Edit `unitree_mujoco/simulate/config.yaml`:
```yaml
robot: "b2w"     # ← change from "go2"
domain_id: 1     # loopback sim domain
interface: "lo"
use_joystick: 0  # keyboard mode — no USB gamepad needed
```

### Environment setup (required in every terminal)

If the machine has ROS installed, source this script before running either the simulator or
the controller. It strips ROS variables that pollute `LD_LIBRARY_PATH` and disable the
Iceoryx shared-memory transport that crashes CycloneDDS on startup:

```bash
source /workspace/near-locomotion-quadruped/scripts/sim2sim_env.sh
```

> **Why this is needed:** ROS 2 sets `LD_LIBRARY_PATH` to its own lib directories. Without
> clearing them the dynamic linker picks up ROS-bundled DDS libraries, causing
> `free(): invalid pointer` or `free(): invalid next size` crashes immediately on startup.

### Run (two terminals)

**Terminal 1 — simulator:**
```bash
sim2sim_env
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate/build
./unitree_mujoco
```

**Terminal 2 — controller** (keep this terminal focused for keyboard input):
```bash
sim2sim_env
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/robots/b2w/build
./b2w_ctrl --network lo
```

> **Note:** The binary is `b2w_ctrl`, not `b2w_controller`. There is no `--config` flag;
> the controller always loads `../config/config.yaml` relative to the binary location.

### Operating sequence

| Step | Key | Result |
|------|-----|--------|
| 1 | *(wait)* | Robot spawns limp in Passive state |
| 2 | `f` | Stands up (FixStand, ~3 s) |
| 3 | `r` | Policy activates (Velocity mode) |
| 4 | `w` / `s` / `a` / `d` | Forward / backward / strafe left / right |
| 5 | `q` / `e` | Yaw CCW / CW |
| 6 | `x` | Return to Passive |

Arrow keys and numpad (NumLock on) also work for velocity commands.

### Replicability — deploying a new trained policy

The sim2sim infrastructure (simulator, controller binary, config) never changes between
training runs. `b2w_ctrl` auto-selects the newest run: `parser_policy_dir` sorts all
timestamp directories under `policy_dir` and picks the last one that contains `exported/`.

**No manual file copying is needed.** `deploy.yaml` is no longer stored inside each policy's
`params/` folder — it lives at a single canonical location:

```
unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml
```

The controller loads it from there on every startup. After training and exporting a new
policy, just start `./b2w_ctrl --network lo` as normal — it picks up the new `policy.onnx`
automatically and reads `deploy.yaml` from `config/`.

> **When to update deploy.yaml:** the file content is determined by `rough_env_cfg.py`. As
> long as you retrain the same task without changing observation terms, scales, or the
> action structure, `config/deploy.yaml` works for every run. If you change the obs layout
> (add/remove terms, change scales), update `config/deploy.yaml` to match before running.

---

### Step 3b — Generate rough terrain (optional)

By default the simulator loads `scene.xml` (flat ground). Generate a terrain scene once,
then switch to it in `config.yaml`.

**Install the one dependency:**
```bash
pip3 install noise --break-system-packages
```

**Generate:**
```bash
cd /workspace/near-locomotion-quadruped/unitree_mujoco/terrain_tool

# Edit terrain_generator.py:
#   ROBOT = "b2w"
#   INPUT_SCENE_PATH  = "../unitree_robots/b2w/scene.xml"   ← must use b2w's own scene.xml
#   OUTPUT_SCENE_PATH = "../unitree_robots/b2w/scene_terrain.xml"
# Then run:
python3 terrain_generator.py
```

> **Always use the robot-specific `scene.xml` as input.** The default `INPUT_SCENE_PATH`
> points to `terrain_tool/scene.xml` which includes `go2.xml`. If you forget to change it,
> MuJoCo will print `XML Error: Error opening file '.../b2w/go2.xml'` and refuse to start.

**Switch to terrain scene** in `unitree_mujoco/simulate/config.yaml`:
```yaml
robot_scene: "scene_terrain.xml"   # terrain
# robot_scene: "scene.xml"         # flat (default)
```

The terrain generator supports: rough ground (random cubes), Perlin heightfield, stairs,
floating stairs, arbitrary boxes and geometry. See [`docs/mujoco_sim2sim.md`](mujoco_sim2sim.md#terrain-generation)
for the full function reference and parameter details.

---

## Key Files

| File | Purpose |
|---|---|
| `robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/agents/rsl_rl_ppo_cfg.py` | Training config — `max_iterations`, network dims, PPO hyperparams |
| `robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/rough_env_cfg.py` | Obs layout, action scales, joint order |
