# near-locomotion-quadruped README

## Contents

<details>
<summary><strong><a href="#1-environment-setup">1. Environment Setup</a></strong></summary>

- [1.1 System Container Was Tested On](#11-system-container-was-tested-on)
- [1.2 What the Container Downloads](#12-what-the-container-downloads)
- [1.3 Quick Start - Dev Container](#13-quick-start---dev-container)
- [1.4 Shell Functions](#14-shell-functions)

</details>

<details>
<summary><strong><a href="#2-mujoco-sim2sim-validation-setup">2. MuJoCo Sim2Sim Validation Setup</a></strong></summary>

- [2.1 Overview](#21-overview)
- [2.2 Prerequisite Installation](#22-prerequisite-installation)
- [2.3 Check this before running sim2sim](#23-check-this-before-running-sim2sim)
- [2.4 Terrain Generation](#24-terrain-generation)
- [2.5 Switching to Gamepad](#25-switching-to-gamepad)

</details>

<details>
<summary><strong><a href="#3-workflow">3. Workflow</a></strong></summary>

- [3.1 Step 1 - Train Teacher in Isaac Lab](#31-step-1---train-teacher-in-isaac-lab)
- [3.2 Step 1b - Watch the Robot Walk in Isaac Sim](#32-step-1b---watch-the-robot-walk-in-isaac-sim)
- [3.3 Step 1c - Distillation + RL Fine-Tuning](#33-step-1c---distillation--rl-fine-tuning)
- [3.4 Step 1d - Evaluation](#34-step-1d---evaluation)
- [3.5 Step 2 - Export to ONNX](#35-step-2---export-to-onnx)
- [3.6 Step 3 - Sim2Sim in MuJoCo](#36-step-3---sim2sim-in-mujoco)
- [3.7 Step 3b - Generate rough terrain](#37-step-3b---generate-rough-terrain)
- [3.8 Step 4 - Sim2Real (to be tested)](#38-step-4---sim2real-to-be-tested)

</details>

<details>
<summary><strong><a href="#4-curriculum-training-with-different-terrain">4. Curriculum Training with Different Terrain</a></strong></summary>

- [4.1 Training Command](#41-training-command)
- [4.2 Sub-Terrains (the default mix)](#42-sub-terrains-the-default-mix)
- [4.3 Worked example: rough-v1 walking policy expert](#43-worked-example-rough-v1-walking-policy-expert)

</details>

## 1. Environment Setup

### 1.1 System Container Was Tested On

<details>
<summary><strong>Container was tested in the following system:</strong></summary>

| Component | Spec |
|---|---|
| **OS** | Ubuntu 24.04.2 LTS (Noble Numbat) |
| **Kernel** | 6.8.0-117-generic |
| **CPU** | Intel Core Ultra 9 275HX (24 cores) |
| **RAM** | 62 GiB |
| **GPU** | NVIDIA GeForce RTX 5090 Laptop GPU (24 GB VRAM) |
| **NVIDIA Driver** | 580.159.03 |
| **CUDA** | 12.8 |
| **Isaac Sim** | 5.1.0 (Python 3.11, torch 2.7.0+cu128) |
| **ROS 2** | Humble (installed via Jammy compat shims on Noble) |

</details>

> Isaac Sim's **Python 3.11** used for all Isaac Lab training and playing; **Python 3.10** for ROS 2. ROS 2 Humble is built for Ubuntu 22.04/Jammy, which ships Python 3.10, so the container installs `libpython3.10` from the deadsnakes PPA even though Noble's own `python3` is 3.12.

> **Driver note:** NVIDIA driver **595 does not work** with Isaac Sim 5.1 - causes GUI to crash on startup ([issue #568](https://github.com/isaac-sim/IsaacSim/issues/568)). Isaac Sim 5.1 only tested on the **580** driver branch at release time and driver 595 introduced changes that broke compatibility. Use driver **580.x** instead.

### 1.2 What the Container Downloads

The Dockerfile pulls the following during `docker build`. Plan for a large first build (~30-40 GB total download).

<details>
<summary><strong>Container downloads the following:</strong></summary>

| What | Source | Size (approx) |
|---|---|---|
| `nvcr.io/nvidia/isaac-sim:5.1.0` base image | NGC (`nvcr.io`) | ~25 GB |
| ROS 2 Humble packages (`ros-humble-ros-base`, `rmw-cyclonedds-cpp`, colcon, compat libs) | `packages.ros.org` | ~300 MB |
| Isaac Sim Python 3.11 deps (`rsl-rl-lib`, `flatdict`, `h5py`, `onnx`, `GitPython`, etc.) | PyPI (`--no-deps`) | ~100 MB |
| `cusrl` | PyPI | ~10 MB |
| Standalone PyTorch venv (`torch`, `torchvision`, `torchaudio` CUDA 12.8 nightly) | `download.pytorch.org` | ~4 GB |

</details>

### 1.3 Quick Start - Dev Container

The repo ships a `.devcontainer/` at its root. Prerequisites:

- NVIDIA GPU host with `nvidia-container-toolkit` installed
- Docker
- VS Code with the **Dev Containers** extension

1. **Clone the repo with its submodules** (`robot_lab`, `unitree_mujoco`, `unitree_rl_lab`):

   ```bash
   git clone https://github.com/vet3whale/near-locomotion-quadruped.git
   cd near-locomotion-quadruped
   git checkout b2w-distillation-training
   ```

2. **Initialise the submodules** (skip if you already used `--recurse-submodules` on the clone):

   ```bash
   git submodule init
   ```

3. **Fetch the submodule contents:**

   ```bash
   git submodule update --recursive
   ```

4. **Open the folder in VS Code and build the dev container.** Open `.devcontainer/devcontainer.json` (or just the repo folder), then either:
   - click the **"Reopen in Container"** prompt VS Code shows, or
   - run **Dev Containers: Reopen in Container** from the Command Palette (`F1`).

   VS Code builds the image from `.devcontainer/Dockerfile` and mounts the repo at `/workspace/near-locomotion-quadruped`. The first build is large (pulls the Isaac Sim base image).

5. **Install Isaac Lab inside the container.** After the container is running, open a terminal inside it and run:

   ```bash
   git clone https://github.com/isaac-sim/IsaacLab.git /workspace/isaaclab \
     && ln -sf /isaac-sim /workspace/isaaclab/_isaac_sim \
     && cd /workspace/isaaclab && TERM=xterm ./isaaclab.sh -i
   ```
    This should be done after **every rebuild of the container.**  

6. **Verify Isaac Sim works.** Run the drop-sphere sanity check (`drop_sphere.py` ships in the repo root). It will open Isaac Sim GUI and drops a physics sphere onto a ground plane. If it renders and the sphere falls, Isaac Sim is working correctly.

   ```bash
   cd /workspace/near-locomotion-quadruped
   /isaac-sim/python.sh drop_sphere.py
   ```

   Close the window when done. If it crashes on startup, check the NVIDIA driver version (see [System Container Was Tested On](#11-system-container-was-tested-on) - driver 595 is known broken).

### 1.4 Shell Functions

The dev container's `~/.bashrc` defines two functions. Call each once per terminal as needed:

| Function | When to call |
|---|---|
| `setup_isaaclab` | Before `train.py`, `play.py` script (need Isaac Lab) | 
| `sim2sim_env` | Before `unitree_mujoco` or `b2w_ctrl` |

## 2. MuJoCo Sim2Sim Validation Setup

This section explains how to set up Sim2Sim validation using MuJoCo.

> **FSM states glossary** (the controller is a finite state machine):
> - **Passive** - motors limp, robot sits on the ground. startup state.
> - **FixStand** - holds a fixed standing pose.
> - **Velocity** - the RL policy is active and driving the robot from velocity commands.
> - **SitDown** - three-phase sit-down (damp, interpolate, then ramp stiffness down) before returning to Passive.

### 2.1 Overview

**Training policy location** (auto-selected by `parser_policy_dir`):
```
robot_lab/logs/rsl_rl/<experiment_name>/<latest-timestamp>/exported/policy.onnx
```

> **Note**: Run `play.py` to convert from `.pt` to `.onnx` format. 

**IMPORTANT**: Set which policy the controller deploys (for sim2sim or sim2real) by opening `unitree_rl_lab/deploy/robots/b2w/config/config.yaml` and editing `policy_dir` to point at the log root of the run you want.   
`parser_policy_dir` function in controller automatically finds most recent timestamp subdirectory that contains an `exported/` folder and loads `policy.onnx` from it.  
See [Step 2 - Export to ONNX](#35-step-2---export-to-onnx) to generate `.onnx` file from a `.pt` checkpoint.

### 2.2 Prerequisite Installation

These steps are required once on the host machine after the first build.

#### 1. System packages

```bash
sudo apt update
sudo apt install -y build-essential python3-pip libglfw3-dev libyaml-cpp-dev libspdlog-dev libboost-all-dev
```

#### 2. unitree_sdk2

```bash
cd ~
git clone https://github.com/unitreerobotics/unitree_sdk2.git
cd unitree_sdk2
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/opt/unitree_robotics
sudo make install
```

#### 3. MuJoCo 3.3.6

```bash
mkdir -p ~/.mujoco && cd ~/.mujoco
curl -L https://github.com/google-deepmind/mujoco/releases/download/3.3.6/mujoco-3.3.6-linux-x86_64.tar.gz -o mujoco-3.3.6-linux-x86_64.tar.gz
tar -xzf mujoco-3.3.6-linux-x86_64.tar.gz

# Symlink into the simulate/ source tree (CMakeLists.txt expects simulate/mujoco/)
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate
ln -s ~/.mujoco/mujoco-3.3.6 mujoco
```

#### 4. Build unitree_mujoco

```bash
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate
mkdir -p build && cd build
cmake ..
make -j4
```

Binary: `unitree_mujoco/simulate/build/unitree_mujoco` - [→ Run it](#run-two-terminals)

#### 5. Build the B2W controller

The ONNX Runtime bundle ships without the unversioned `.so` symlink that the linker needs.
Create it once before building:

```bash
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/thirdparty/onnxruntime-linux-x64-1.22.0/lib
ln -s libonnxruntime.so.1.22.0 libonnxruntime.so
```

Then build:

```bash
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/robots/b2w
mkdir -p build && cd build
cmake .. && make
```

Binary: `unitree_rl_lab/deploy/robots/b2w/build/b2w_ctrl` - [→ Run it](#run-two-terminals)

### 2.3 Check this before running sim2sim

#### `unitree_mujoco/simulate/config.yaml`

```yaml
robot: "b2w"
robot_scene: "scene_terrain.xml"   # ← the checked-in default on this branch (NOT scene.xml)
domain_id: 0
interface: "lo"       # loopback for sim2sim
use_joystick: 0       # 0 = no USB gamepad required (keyboard mode)
```

#### MJCF model

Confirm `unitree_mujoco/unitree_robots/b2w/` exists and contains `b2w.xml`.

### 2.4 Terrain Generation

Mujoco simulator ships with a flat ground scene (`scene.xml`) for each robot. So, use the terrain generator tool to produce a `scene_terrain.xml` that adds obstacles, rough ground, or Perlin heightfields.  

#### Prerequisites (once)

```bash
python3 -m pip install noise opencv-python-headless --break-system-packages
```

> The system Python on Ubuntu 24.04 is externally-managed; `--break-system-packages` is safe for these small packages.

#### Generate terrain

The following runs the generator and then patches the output:

```bash
cd /workspace/near-locomotion-quadruped/unitree_mujoco/terrain_tool
python3 terrain_generator.py

# Fix the go2 references the generator leaves in the output
sed -i 's/model="go2 scene"/model="b2w scene"/' ../unitree_robots/b2w/scene_terrain.xml
sed -i 's|<include file="go2.xml" />|<include file="b2w.xml"/>|' ../unitree_robots/b2w/scene_terrain.xml
```

#### Switch between flat and terrain scenes

In `unitree_mujoco/simulate/config.yaml`:
```yaml
# Flat ground:
robot_scene: "scene.xml"

# Terrain (the checked-in value on this branch):
robot_scene: "scene_terrain.xml" 
```

Then restart `./unitree_mujoco`.

### 2.5 Switching to Gamepad

To use a physical USB gamepad (or the unitree_mujoco software joystick) instead of keyboard
velocity commands:

**In `b2w/config/deploy.yaml`**:
<details>
<summary><strong>Comment out keyboard_velocity_commands + Uncomment velocity_commands:</strong></summary>

```yaml
observations:
  # Uncomment this (reads the controller paired to the B2W via lowstate->joystick;
  # ranges come from commands.base_velocity.ranges, so it takes no params):
  velocity_commands:
    params: {}
    clip: null
    scale: [1.0, 1.0, 1.0]
    history_length: 1
  # Comment out this:
  # keyboard_velocity_commands:
  #   params: {command_name: base_velocity}
  #   clip: null
  #   scale: [1.0, 1.0, 1.0]
  #   history_length: 1
```

</details>

**In `simulate/config.yaml`**:
```yaml
use_joystick: 1   # requires USB gamepad at /dev/input/js0
```

FSM transitions (Passive↔FixStand↔Velocity) still work via gamepad buttons even in keyboard
mode, because the `transitions` (DDS joystick) and `keyboard_transitions` blocks coexist.

## 3. Workflow

Train a locomotion policy in Isaac Lab, watch it in the Isaac Sim GUI, export it to ONNX, and validate it in MuJoCo sim2sim.

### 3.1 Step 1 - Train Teacher in Isaac Lab

Open a terminal and set up the Isaac Lab Python environment first. Each terrain expert is trained as its own teacher - run the command for the expert you want.

**The following example is for training Teacher Policy:**
```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1 \
  --headless --max_iterations 5000   # without --max_iterations it runs for 20000 iterations
```

<details>
<summary><strong>Resume from a checkpoint</strong></summary>

**Latest checkpoint:**
```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless \
  --resume
```

**Specific run:**
```bash
setup_isaaclab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless \
  --resume \
  --load_run 2026-05-24_05-47-04
```
</details>

### 3.2 Step 1b - Watch the Robot Walk in Isaac Sim

Use `play.py` to load a checkpoint, watch the robot in the Isaac Sim GUI, and export the policy. Key flags:

- `--task` - environment to load (normally the same environment used for training).
- `--load_run <timestamp>` - load a specific run; omit to auto-load the most recent.
- `--num_envs <n>` - number of parallel environments (defaults to 64). Ignored under `--keyboard`, which always forces 1.
- `--keyboard` - steer interactively. Drives `base_velocity` from the keyboard (velocity tasks) and pins the scene to a single environment.

#### Run play.py with keyboard control

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1 \
  --load_run 2026-07-07_06-00-00_height_scan_enabled \
  --num_envs 1 \
  --keyboard
```

> Remove `--load_run` to auto-load the most recent run.

<details>
<summary><strong>Click to expand Keyboard controls table</strong></summary>

| Key | Action |
|---|---|
| Numpad 8 | Forward |
| Numpad 2 | Backward |
| Numpad 4 | Strafe left |
| Numpad 6 | Strafe right |
| Numpad 7 | Rotate left |
| Numpad 9 | Rotate right |
| L | Reset velocity to zero |

</details>

<details>
<summary><strong>Out-of-distribution check - play the rough-v1 teacher on Rough-v0</strong></summary>

Load the `v1` checkpoint into the `v0` task. `--checkpoint` takes an explicit path, so it skips the
`logs/rsl_rl/<experiment_name>/` lookup that would otherwise search `unitree_b2w_rough/`:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --checkpoint logs/rsl_rl/unitree_b2w_rough_v1/2026-07-07_06-00-00_height_scan_enabled/model_6500.pt \
  --num_envs 1 \
  --keyboard
```

No config edit is needed: `v0` and `v1` differ only in the terrain generator, so the observation and
action spaces match and the `v1` weights load directly.

</details>

### 3.3 Step 1c - Distillation + RL Fine-Tuning

Distillation trains one **student** to copy one or more privileged PPO **teachers**, using MSE loss
on the student's own on-policy rollouts.

#### Phase 1 - Train the teachers (PPO)

The teachers are the privileged PPO policies trained in [Step 1](#31-step-1---train-teacher-in-isaac-lab).


#### Phase 2 - List the active teachers in `teachers.txt`

Open [`teachers.txt`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/teachers.txt)
and confirm it lists exactly the experts you want, each pointing at the correct checkpoint.

#### Phase 3 - Train the depth student

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --num_envs 512 \
  --headless
```

#### Phase 4 - Play the distilled student

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --num_envs 1 \
  --keyboard
```

> The `--agent` flag selects `DistillationRunner`, which is the only runner
> that knows how to read the `student_state_dict` key in a distillation checkpoint.

<details>
<summary><strong>Out-of-distribution check - play the distilled student on Rough-v0</strong></summary>

To spawn it on terrain it never saw, edit
[`multiexpert_teacher_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/multiexpert_teacher_env_cfg.py)
and uncomment the last three lines so they override the merged terrain and the pit-floor spawn:

```python
gen, column_to_expert = build_multiexpert_terrain(entries)
self.scene.terrain.terrain_generator = gen
self.column_to_expert = column_to_expert

# Eval the student on the stock Rough-v0 terrain instead of the merged expert terrain
from isaaclab.terrains.config.rough import ROUGH_TERRAINS_CFG
self.scene.terrain.terrain_generator = copy.deepcopy(ROUGH_TERRAINS_CFG)
```

Then re-run the same Phase 4 play command. It now spawns the student on the stock `Rough-v0` mix
(pyramid stairs, boxes, random rough, slopes) from [4.2](#42-sub-terrains-the-default-mix) instead of
the merged expert terrain.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --num_envs 1 \
  --keyboard --seed 1
```

> Comment the line back out before distilling again. Left uncommented it changes the *training*
> terrain, which breaks the per-column expert routing the multi-expert run depends on.

</details>

#### Phase 5 - PPO fine-tune the student

The student weights come in through
`--init_actor_from`, which accepts either a distillation or a PPO checkpoint.

Fine-tuning runs in **two phases**. 
1. Phase A: Actor arrives pre-trained but critic starts from scratch, so freeze actor and train only critic.
2. Phase B: Unfreezes actor and trains both.

`--freeze_actor` also pins the LR schedule to `fixed`. With the actor frozen the KL is ~0, so the
adaptive schedule would otherwise keep ramping the LR up and destabilise the critic.

**Phase 5A - critic only** (actor frozen):

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
    --task RobotLab-Isaac-Velocity-Student-Finetune-Unitree-B2W-v0 \
    --headless \
    --num_envs 512 \
    --max_iterations 4000 \
    --freeze_actor \
    --init_actor_from logs/rsl_rl/unitree_b2w_multiexpert/2026-07-15_14-19-16_walking_expert_distillation/model_25998.pt \
    --logger wandb \
    --log_project_name b2w_student_finetune \
    --run_name phaseA_4000iter
```

**Phase 5B - actor + critic.** `--init_critic_from` points at the last checkpoint phase A wrote:

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
    --task RobotLab-Isaac-Velocity-Student-Finetune-Unitree-B2W-v0 \
    --headless \
    --num_envs 512 \
    --max_iterations 10000 \
    --init_actor_from logs/rsl_rl/unitree_b2w_multiexpert/2026-07-15_14-19-16_walking_expert_distillation/model_25998.pt \
    --init_critic_from logs/rsl_rl/unitree_b2w_student_finetune/2026-07-20_08-06-05_phaseA_4000iter/model_3999.pt \
    --logger wandb \
    --log_project_name b2w_student_finetune \
    --run_name phaseB_10000iter
```

#### Phase 6 - Play the fine-tuned student

The fine-tuned student is a PPO checkpoint, so drop the `--agent` flag used in Phase 4:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Student-Finetune-Unitree-B2W-v0 \
  --num_envs 1 \
  --keyboard
```

<details>
<summary><strong>Out-of-distribution check - play the fine-tuned student on Rough-v0</strong></summary>

To test it on a terrain it never saw,
edit [`student_finetune_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/student_finetune_env_cfg.py)
and uncomment the last three lines so the terrain and spawn overrides apply:

```python
self.scene.terrain.terrain_generator = ROUGH_TERRAINS_FT_CFG
# Eval the student on the stock Rough-v0 terrain instead of the FT obstacle terrain
import copy
from isaaclab.terrains.config.rough import ROUGH_TERRAINS_CFG
self.scene.terrain.terrain_generator = copy.deepcopy(ROUGH_TERRAINS_CFG)
```

Then re-run the same Phase 6 play command. It now spawns the student on the stock `Rough-v0` mix
(pyramid stairs, boxes, random rough, slopes) instead of the fine-tune terrain.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Student-Finetune-Unitree-B2W-v0 \
  --num_envs 1 \
  --keyboard --seed 1
```

> Comment the line back out before training again, or the next fine-tune run trains on the OOD
> terrain and the check stops being out-of-distribution.

</details>

### 3.4 Step 1d - Evaluation

Score a policy the way the paper's Table 4 does: 1000 robots, one fixed velocity command, terrain
randomized at 90% of max training difficulty. A robot succeeds if it covers 4 m along the command
without falling. A run takes about a minute.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/evaluation/evaluate.py --policy student_finetune
```

Four flags, all optional except `--policy`:

| Flag | Values | Default |
| --- | --- | --- |
| `--policy` | `expert`, `student`, `student_finetune`, or a path to a `model_*.pt` | required |
| `--terrain` | `finetune`, `rough_v1`, `rough_v0` | `finetune` |
| `--num_envs` | robots to roll out | `1000` |
| `--gui` | watch it instead of running headless | off |

All three policies run in the same environment, so the numbers compare directly. Each run prints
the success rate and appends a row to `evaluation_table.csv`.

```bash
# the full comparison
python scripts/evaluation/evaluate.py --policy expert && \
python scripts/evaluation/evaluate.py --policy student && \
python scripts/evaluation/evaluate.py --policy student_finetune
```

Success rate in %, 1000 rollouts per cell:

| terrain | expert_success | student_success | student_finetune_success |
| --- | --- | --- | --- |
| finetune | 93.3 | 82.8 | 96.1 |

<details>
<summary><strong>Steps to change expert and evaluate</strong></summary>

Two edits to [`evaluate.py`](../robot_lab/scripts/evaluation/evaluate.py). The new terrain has to
belong to a registered task, since `TERRAINS` maps names to task ids.

**1. Point the `expert` entry at the new checkpoint:**

```python
POLICIES = {
    "expert": (
        "logs/rsl_rl/unitree_b2w_staircase_teacher/<run>/model_N.pt",
        "privileged PPO expert trained on staircases",
    ),
    ...
}
```

**2. Add its terrain:**

```python
TERRAINS = {
    "rough_v0": "RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0",
    "rough_v1": "RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1",
    "finetune": TASK,
    "staircase": "RobotLab-Isaac-Velocity-Staircase-Teacher-Unitree-B2W-v0",
}
```

`--terrain` takes its choices from this dict, so the new name works immediately.

```bash
python scripts/evaluation/evaluate.py --policy expert --terrain staircase
```

</details>

### 3.5 Step 2 - Export to ONNX

`play.py` exports on startup, so the same script that plays a policy also writes its `.onnx`. Export
the fine-tuned student from [Phase 5](#phase-5---ppo-fine-tune-the-student):

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Student-Finetune-Unitree-B2W-v0 \
  --headless
```
> Can **Ctrl+C** once it runs without crashing - the export has already happened by then.

The exported policy will be at:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_student_finetune/<timestamp>/exported/policy.onnx
```

Swap `--task` for any other trained policy to export that one instead - the file lands under that
task's own `<experiment_name>`.

> **The student export is stateful.** The CNN+LSTM student carries hidden state between steps, so its
> exporter threads `h_in`/`c_in` in and `h_out`/`c_out` out as extra ONNX tensors. A caller must feed
> the previous step's outputs back in and zero them on reset. A feed-forward PPO teacher has no such
> inputs - anything consuming the student's ONNX has to be written for the recurrent signature.

### 3.6 Step 3 - Sim2Sim in MuJoCo

> To be updated to accomodate for the depth student.

Run the exported ONNX policy against the MuJoCo simulator over DDS on loopback.
No physical robot or gamepad required - control is via keyboard.

> **First time only:** complete the one-time setup, build, and `simulate/config.yaml` config
> under [MuJoCo Sim2Sim Validation Setup](#2-mujoco-sim2sim-validation-setup) - system packages, `unitree_sdk2`,
> MuJoCo, the ONNX Runtime symlink, building `unitree_mujoco` + `b2w_ctrl`, and setting
> `robot: "b2w"`. The steps below assume that is done.

#### Run (two terminals)

[← Build unitree_mujoco](#4-build-unitree_mujoco) · [← Build b2w_ctrl](#5-build-the-b2w-controller)

**Terminal 1 - simulator:**
```bash
sim2sim_env
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate/build
./unitree_mujoco
```

**Terminal 2 - controller** (keep this terminal focused for keyboard input):
```bash
sim2sim_env
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/robots/b2w/build
./b2w_ctrl --network lo
```
> **Note:** If the robot falls on its back, just **Ctrl+C** and rerun the 2 commands above. 

#### Operating sequence

<details>
<summary><strong>Click to expand Operating sequence table</strong></summary>

| Step | Key | Result |
|------|-----|--------|
| 1 | *(wait)* | Robot spawns limp in Passive state |
| 2 | `f` | Stands up (FixStand, ~3 s) |
| 3 | `r` | Policy activates (Velocity mode). Also latches speed gear 3 (33% of max) |
| 4 | `q`...`p` | Select speed gear. **Required**: at gear 0 the numpad keys do nothing |
| 5 | Numpad `8` / `2` / `4` / `6` | Forward / backward / strafe left / right |
| 6 | Numpad `7` / `9` | Yaw CCW / CW |
| 7 | `x` | Return to sitdown |

</details>

#### Speed gear

Command = numpad direction (momentary) x gear scale (latched, starts at 0).

| Key | `q` | `w` | `e` | `r` | `t` | `y` | `u` | `i` | `o` | `p` |
|---|---|---|---|---|---|---|---|---|---|---|
| Gear | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| Share of max | 0% | 11% | 22% | 33% | 44% | 56% | 67% | 78% | 89% | 100% |

`r` is both the FSM transition into Velocity and gear 3, which is why the robot moves at all
before you touch a gear key. `q` stops it without leaving Velocity.

> Pressing `x` returns the robot to Passive - it slowly sits down and goes limp.

### 3.7 Step 3b - Generate rough terrain

Check how to set it up under [B2W MuJoCo Sim2Sim Validation → Terrain Generation](#24-terrain-generation).

> The terrain generator supports: rough ground (random cubes), Perlin heightfield, stairs,
> floating stairs, arbitrary boxes and geometry.

### 3.8 Step 4 - Sim2Real (to be tested)

> **The current depth student cannot be deployed.** The C++ controller has no depth capture, no depth
> preprocessing, and no image tensor inputs. This section describes the deployment path for the
> **old blind 57-element** policy generation only.

## 4. Curriculum Training with Different Terrain

### 4.1 Training Command

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0
```

---

### 4.2 Sub-Terrains (the default mix)

The default `v0` terrain is a grid of tiles built from `ROUGH_TERRAINS_CFG` (defined in `isaaclab/terrains/config/rough.py`). Six terrain types are mixed together, each taking a proportion of the columns:

<details>
<summary><strong>Click to expand table</strong></summary>

| Terrain Type | Proportion | Difficulty Parameter | Description |
|---|---|---|---|
| `pyramid_stairs` | 20% | step height: 5 cm → 23 cm | Steps rising to a raised centre platform - robot spawns on top and must descend |
| `pyramid_stairs_inv` | 20% | step height: 5 cm → 23 cm | Steps cut down to a sunken centre platform - robot spawns on the pit floor and must climb out |
| `boxes` | 20% | box height: 5 cm → 20 cm | Grid of randomly-sized raised blocks spread across the tile |
| `random_rough` | 20% | noise amplitude: 2 cm → 10 cm | Heightfield with random uniform noise - uneven bumpy ground |
| `hf_pyramid_slope` | 10% | slope angle: 0° → ~22° | Smooth ramp peaking at the centre - robot spawns at the top and must descend |
| `hf_pyramid_slope_inv` | 10% | slope angle: 0° → ~22° | Smooth concave bowl - robot spawns at the lowest point and must climb out |

</details>

Each tile is **8 m × 8 m**. The full terrain grid is **10 rows × 20 columns**, giving 200 tiles in total. The difficulty parameter for each terrain type scales **linearly from its minimum to its maximum** across the 10 rows - row 0 has the easiest version of each terrain, row 9 has the hardest.

### 4.3 Worked example: rough-v1 walking policy expert

This example fills in the details on how **rough-v1**, the general walking-policy expert was created.

The defining property: rough-v1 is a **pure terrain swap**. Rewards, observations, and actions are inherited unchanged from the base rough task ([`rough_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/rough_env_cfg.py)).

The task stays inside the velocity folder:

```text
robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/
```

The registered task is:

```text
RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1
```

#### Step 1 - Choose the terrain composition

The terrain is defined in:

```text
rough_env_cfg_v1.py
```

The config creates a new `ROUGH_TERRAINS_V1_CFG` instead of editing the shared base terrain (`ROUGH_TERRAINS_CFG` is left untouched, since `v0` shares it). Tiles are 8 m x 8 m, 10 difficulty rows x 20 columns, and mix three terrain families:

| Terrain piece | Share | Params | What it gives the robot |
|---|---:|---|---|
| `MeshInvertedPyramidStairsTerrainCfg` | 30% | step height 5 cm, tread 27.5 cm | sharp, solid stair edges |
| `HfInvertedPyramidStairsTerrainCfg` | 30% | step height 5 cm, tread 27.5 cm | smoother heightfield stairs |
| `HfInvertedPyramidSlopedTerrainCfg` | 20% | slope 0.176 rad (~10°) | a continuous outward incline |
| `HfDiscreteObstaclesTerrainCfg` | 20% | 8 boxes, height 5-15 cm, width 0.4-1.0 m | scattered low obstacles to step over |

So the mix is **60% stairs, 20% slopes, 20% obstacles**. Training on all three at once is what makes this a general walking expert rather than a specialist.

#### Step 2 - Add the env config

`UnitreeB2WRoughEnvCfgV1` subclasses the normal B2W rough velocity config:

```python
class UnitreeB2WRoughEnvCfgV1(UnitreeB2WRoughEnvCfg):
```

Inside `__post_init__`, it makes only the changes needed to run the new terrain:

| Change | Why |
|---|---|
| `self.scene.terrain.terrain_generator = ROUGH_TERRAINS_V1_CFG` | use the mixed v1 terrain |
| `self.sim.physx.gpu_collision_stack_size = 2**27` | stair meshes + obstacles spawn many contacts; raise the GPU collision stack from 64 MB to 128 MB |
| `curriculum = True` on the new terrain generator (if `terrain_levels` is active) | keep the row-by-row difficulty curriculum |
| re-run `disable_zero_weight_rewards()` for this subclass | the parent only does that automatically for its own base class name |

#### Step 3 - Add a PPO runner config

The runner config is added in:

```text
agents/rsl_rl_ppo_cfg.py
```

It subclasses the normal B2W rough PPO settings and only changes the experiment name:

```python
class UnitreeB2WRoughV1PPORunnerCfg(UnitreeB2WRoughPPORunnerCfg):
    def __post_init__(self):
        super().__post_init__()
        self.experiment_name = "unitree_b2w_rough_v1"
```

This keeps the training algorithm the same while saving logs and checkpoints under a separate run folder (`logs/rsl_rl/unitree_b2w_rough_v1/`).

#### Step 4 - Register the gym task id

The task is registered in:

```text
__init__.py
```

The registration connects the task name to the config classes (PPO for training plus the distillation entry points, since rough-v1 is also used as a teacher):

```python
gym.register(
    id="RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": f"{__name__}.rough_env_cfg_v1:UnitreeB2WRoughEnvCfgV1",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UnitreeB2WRoughV1PPORunnerCfg",
        "rsl_rl_distillation_cfg_entry_point": (
            f"{agents.__name__}.rsl_rl_distillation_cfg:UnitreeB2WRoughDistillationRunnerCfg"
        ),
        "rsl_rl_distillation_recurrent_cfg_entry_point": (
            f"{agents.__name__}.rsl_rl_distillation_cfg:UnitreeB2WRoughDistillationRunnerRecurrentCfg"
        ),
    },
)
```

`rsl_rl_cfg_entry_point` is the default the `--agent` flag resolves to, so plain `train.py` picks up
PPO. The two distillation entry points are selected explicitly with `--agent`, and they exist here
because rough-v1 is also listed in `teachers.txt` as a distillation teacher.

Train the walking expert with:

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1
```