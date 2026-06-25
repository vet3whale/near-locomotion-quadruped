# Training to Deployment Pipeline for Unitree B2W (near-locomotion-quadruped repo)

> **Branch:** this documentation lives on the `b2w-rough-walking` branch of the main repo.

The B2W has 16 DOF: 12 leg joints (FR/FL/RR/RL × hip/thigh/calf) controlled by position PD, and 4 wheel joints (FR/FL/RR/RL foot). Three submodule repos work together:

| Repo | Role |
|---|---|
| `robot_lab/` | Isaac Lab task definitions, training config, and `train.py` / `play.py` scripts - where the RL policy is trained and exported to ONNX |
| `unitree_rl_lab/` | C++ deployment controller (`deploy/robots/b2w/`) that loads the ONNX policy and sends joint commands over DDS |
| `unitree_mujoco/` | MuJoCo simulator that receives DDS commands and simulates the B2W - used for sim2sim validation before deploying to the real robot |

RL policy trained in `robot_lab` --> exported to ONNX via `play.py` --> C++ controller in `unitree_rl_lab` loads that ONNX & runs it against either `unitree_mujoco` (sim2sim) or the real robot (sim2real) over DDS.

## Table of Contents

<ul>
  <li><a href="#1-repository-layout">1. Repository Layout</a></li>
  <li><details><summary><a href="#2-environment-setup">2. Environment Setup</a></summary><ul>
    <li><a href="#21-system-container-was-tested-on">2.1 System Container Was Tested On</a></li>
    <li><a href="#22-what-the-container-downloads">2.2 What the Container Downloads</a></li>
    <li><a href="#23-quick-start---dev-container">2.3 Quick Start - Dev Container</a></li>
    <li><a href="#24-shell-functions">2.4 Shell Functions</a></li>
    <li><a href="#25-reference-----load_actor_only-flag">2.5 Reference - <code>--load_actor_only</code> flag</a></li>
  </ul></details></li>
  <li><details><summary><a href="#3-mujoco-sim2sim-validation-setup">3. MuJoCo Sim2Sim Validation Setup</a></summary><ul>
    <li><a href="#31-overview">3.1 Overview</a></li>
    <li><a href="#32-prerequisite-installation">3.2 Prerequisite Installation</a></li>
    <li><a href="#33-check-this-before-running-sim2sim">3.3 Check this before running sim2sim</a></li>
    <li><a href="#34-terrain-generation">3.4 Terrain Generation</a></li>
    <li><a href="#35-switching-to-gamepad">3.5 Switching to Gamepad</a></li>
    <li><a href="#36-code-changes-made">3.6 Code Changes Made</a></li>
  </ul></details></li>
  <li><details><summary><a href="#4-workflow">4. Workflow</a></summary><ul>
    <li><a href="#41-step-1---train-teacher-in-isaac-lab">4.1 Step 1 - Train Teacher in Isaac Lab</a></li>
    <li><a href="#42-step-1b---watch-the-robot-walk-in-isaac-sim">4.2 Step 1b - Watch the Robot Walk in Isaac Sim</a></li>
    <li><a href="#43-step-1c---distillation-student-teacher">4.3 Step 1c - Distillation (Student-Teacher)</a></li>
    <li><a href="#44-step-2---export-to-onnx">4.4 Step 2 - Export to ONNX</a></li>
    <li><a href="#45-step-2a---evaluate-policies-per-level-evaluation-csv">4.5 Step 2a - Evaluate Policies (Per-Level Evaluation CSV)</a></li>
    <li><a href="#46-step-3---sim2sim-in-mujoco">4.6 Step 3 - Sim2Sim in MuJoCo</a></li>
    <li><a href="#47-step-3b---generate-rough-terrain">4.7 Step 3b - Generate rough terrain</a></li>
    <li><a href="#48-step-4---sim2real-to-be-tested">4.8 Step 4 - Sim2Real (to be tested)</a></li>
  </ul></details></li>
  <li><details><summary><a href="#5-curriculum-training-with-different-terrain">5. Curriculum Training with Different Terrain</a></summary><ul>
    <li><a href="#51-training-command">5.1 Training Command</a></li>
    <li><a href="#52-sub-terrains-the-default-mix">5.2 Sub-Terrains (the default mix)</a></li>
    <li><a href="#53-terrain-difficulty-curriculum">5.3 Terrain Difficulty Curriculum</a></li>
    <li><a href="#54-plug-in-a-different-terrain">5.4 Plug in a different terrain</a></li>
    <li><a href="#55-worked-example-staircaseup-teacher">5.5 Worked example: StaircaseUp teacher</a></li>
    <li><a href="#56-multi-expert-terrain">5.6 Multi-Expert Terrain</a></li>
  </ul></details></li>
  <li><details><summary><a href="#6-evaluation-matrix">6. Evaluation Matrix</a></summary><ul>
    <li><a href="#61-command">6.1 Command</a></li>
    <li><a href="#62-how-it-picks-terrains">6.2 How it picks terrains</a></li>
    <li><a href="#63-evaluation-settings">6.3 Evaluation Settings</a></li>
    <li><a href="#64-what-the-csv-records">6.4 What the CSV Records</a></li>
    <li><a href="#65-files-and-reasoning">6.5 Files and Reasoning</a></li>
  </ul></details></li>
  <li><details><summary><a href="#7-skills-trained-on">7. Skills Trained On</a></summary><ul>
    <li><a href="#71-successfully-trained-on">7.1 Successfully trained on</a></li>
    <li><a href="#72-what-we-want-to-train-on-next">7.2 What we want to train on next</a></li>
  </ul></details></li>
  <li><details><summary><a href="#8-b2w-config-verify-before-sim2real">8. B2W Config (Verify Before Sim2Real)</a></summary><ul>
    <li><a href="#81-source-of-truth---unitreepy">8.1 Source of Truth - unitree.py</a></li>
    <li><a href="#82-checklist---verify-before-sim2real">8.2 Checklist - Verify Before Sim2Real</a></li>
    <li><a href="#83-dcmotor-speed-torque-matching-in-mujoco">8.3 DCMotor Speed-Torque Matching in MuJoCo</a></li>
  </ul></details></li>
  <li><details><summary><a href="#9-challenges-faced">9. Challenges Faced</a></summary><ul>
    <li><a href="#91-fixstand-wheel-skid---bug-that-passed-in-sim-but-failed-on-the-real-robot">9.1 FixStand wheel skid - bug that passed in sim but failed on the real robot</a></li>
  </ul></details></li>
  <li><details><summary><a href="#10-deriving-π-in-rl">10. Deriving π in RL</a></summary><ul>
    <li><a href="#101-defining-q-function">10.1 Defining Q-function</a></li>
  </ul></details></li>
  <li><details><summary><a href="#11-proximal-policy-optimisation-ppo-teacher">11. Proximal Policy Optimisation: PPO (Teacher)</a></summary><ul>
    <li><a href="#111-hyperparameters">11.1 Hyperparameters</a></li>
    <li><a href="#112-the-combined-ppo-loss">11.2 The Combined PPO Loss</a></li>
    <li><a href="#113-clipped-surrogate-objective">11.3 Clipped Surrogate Objective</a></li>
    <li><a href="#114-value-critic-loss">11.4 Value (Critic) Loss</a></li>
    <li><a href="#115-entropy-bonus">11.5 Entropy Bonus</a></li>
    <li><a href="#116-generalised-advantage-estimation-gae">11.6 Generalised Advantage Estimation (GAE)</a></li>
    <li><a href="#117-adaptive-kl-based-learning-rate-schedule">11.7 Adaptive KL-based learning-rate schedule</a></li>
    <li><a href="#118-on-policy-data-is-used">11.8 On-Policy data is used</a></li>
    <li><a href="#119-applying-the-gradients">11.9 Applying the gradients</a></li>
    <li><a href="#1110-privileged-learning">11.10 Privileged Learning</a></li>
  </ul></details></li>
  <li><details><summary><a href="#12-distillation-using-dagger-student">12. Distillation using DAGGER (Student)</a></summary><ul>
    <li><a href="#121-teacher-student-distillation-training">12.1 Teacher-Student Distillation Training</a></li>
    <li><details><summary><a href="#122-dagger-dataset-aggregation">12.2 DAGGER (Dataset Aggregation)</a></summary><ul>
      <li><a href="#1221-behaviour-cloning">12.2.1 Behaviour Cloning</a></li>
      <li><a href="#1222-dagger">12.2.2 DAgger</a></li>
      <li><a href="#1223-rsl-rl-implementation-dagger">12.2.3 RSL-RL Implementation: DAgger</a></li>
    </ul></details></li>
  </ul></details></li>
  <li><details><summary><a href="#13-code-walkthrough-trainpy">13. Code Walkthrough: train.py</a></summary><ul>
    <li><a href="#131-ppo">13.1 PPO</a></li>
    <li><a href="#132-distillation-mlp-student">13.2 Distillation (MLP Student)</a></li>
    <li><a href="#133-distillation-lstm-student">13.3 Distillation (LSTM Student)</a></li>
    <li><a href="#134-multi-expert-distillation-lstm-student">13.4 Multi-Expert Distillation (LSTM Student)</a></li>
  </ul></details></li>
</ul>

---
## 1. Repository Layout

<details>
<summary><strong>Key Folders:</strong></summary>

```
near-locomotion-quadruped/
├── drop_sphere.py                                     ← Isaac Sim sanity check (ships in repo root)
├── robot_lab/                                         ← train, eval & export (Isaac Lab)
│   ├── source/robot_lab/tasks/.../unitree_b2w/        ← task definitions (see note below)
│   │   ├── rough_env_cfg.py, flat_env_cfg.py          ← v0 rough & flat tasks
│   │   ├── staircaseup_teacher_env_cfg.py             ← stairs-climbing teacher terrain
│   │   ├── slopeup_teacher_env_cfg.py                 ← slope-climbing teacher terrain
│   │   ├── agents/rsl_rl_ppo_cfg.py                   ← PPO runner cfgs (per-experiment log dirs)
│   │   └── __init__.py                                ← gym.register task ids
│   ├── scripts/reinforcement_learning/rsl_rl/
│   │   ├── train.py, play.py                          ← train, watch, export ONNX
│   │   └── play_cs.py                                 ← USD-map play
│   └── scripts/evaluation/
│       ├── evaluation.py                              ← orchestrator that fills the per-level eval CSV
│       └── eval_worker.py                             ← Isaac eval worker (one policy/terrain rollout)
│
├── unitree_mujoco/                                    ← sim2sim (MuJoCo)
│   ├── simulate/
│   │   └── config.yaml                               ← set robot, domain_id, scene
│   └── unitree_robots/b2w/                           ← B2W MJCF model + scene XMLs
│
└── unitree_rl_lab/                                    ← deployment (C++ controller)
    └── deploy/
        ├── include/FSM/FSMState.h                     ← keyboard FSM transitions
        ├── include/FSM/State_SitDown.h                ← two-phase sit-down state
        ├── include/.../observations/observations.h   ← joint_pos_rel_without_wheel
        └── robots/b2w/
            ├── config/config.yaml                     ← FSM keys, policy_dir, PD gains
            ├── config/deploy.yaml                     ← observation & action layout
            ├── main.cpp                               ← keyboard init, DDS domain
            └── src/State_RLBase.cpp                   ← leg PD + wheel velocity hybrid
```

> **Note**: `source/robot_lab/tasks/.../unitree_b2w/` refers to `robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/`

</details>

---

## 2. Environment Setup

### 2.1 System Container Was Tested On

<details>
<summary><strong>Containter was tested in the following system:</strong></summary>

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

> Isaac Sim's **Python 3.11** used for all Isaac Lab training and playing; **Python 3.12** for ROS 2.

> **Driver note:** NVIDIA driver **595 does not work** with Isaac Sim 5.1 - causes GUI to crash on startup ([issue #568](https://github.com/isaac-sim/IsaacSim/issues/568)). Isaac Sim 5.1 only tested on the **580** driver branch at release time and driver 595 introduced changes that broke compatibility. Use driver **580.x** instead.

### 2.2 What the Container Downloads

The Dockerfile pulls the following during `docker build`. Plan for a large first build (~30–40 GB total download).

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

> The standalone PyTorch venv (last row) is for non-Isaac tooling only. Comment it out in the Dockerfile to speed up builds if you don't need it.

### 2.3 Quick Start - Dev Container

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
   This clones Isaac Lab, symlinks the Isaac Sim install so Isaac Lab can find it, then runs the Isaac Lab installer (`-i`) which sets up all Isaac Lab Python extensions. `TERM=xterm` is needed because the container may not set a terminal type by default.

6. **Verify Isaac Sim works.** Run the drop-sphere sanity check (`drop_sphere.py` ships in the repo root). It will open Isaac Sim GUI and drops a physics sphere onto a ground plane. If it renders and the sphere falls, Isaac Sim is working correctly.

   ```bash
   cd /workspace/near-locomotion-quadruped
   /isaac-sim/python.sh drop_sphere.py
   ```

   Close the window when done. If it crashes on startup, check the NVIDIA driver version (see [System Container Was Tested On](#21-system-container-was-tested-on) - driver 595 is known broken).

### 2.4 Shell Functions

The dev container's `~/.bashrc` defines two functions. Call each once per terminal as needed:

| Function | When to call | What it does |
|---|---|---|
| `setup_isaaclab` | Before `train.py`, `play.py` script (need Isaac Lab) | [See function definition](../../../isaac-sim/.bashrc#L134-L161) |
| `sim2sim_env` | Before `unitree_mujoco` or `b2w_ctrl` | [See function definition](../../../isaac-sim/.bashrc#L165-L169) |

<details>
<summary>Steps to load flat terrain policy to rough terrain environment:</summary>  

`--load_actor_only` flag (Not necessary for distillation - for rough & flat terrain)

To load a flat-terrain checkpoint into the rough-terrain task, you **must** pass `--load_actor_only`:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --checkpoint /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_flat/<timestamp>/model_<N>.pt \
  --num_envs 1 --keyboard --real-time --load_actor_only
```

Without it, `runner.load` will crash. The reason is that the actor and critic have different input sizes between the two tasks:

| Network | Input (flat task) | Input (rough task) |
|---|---|---|
| Actor | 57 (base obs only) | 57 (base obs only) |
| Critic | 60 (base obs + 3 extras) | 247 (base obs + height scans + privileged state) |

The rough critic receives privileged observations, such as height scans, contact forces, terrain geometry, that flat critic doesn't need --> So never saw. 
`play.py` still looks for critic's input, so by passing in `--load_actor_only`, only actor with 57 base observations is used.
</details>

---

## 3. MuJoCo Sim2Sim Validation Setup

This section explains how to set up Sim2Sim validation using MuJoCo.

> **FSM states glossary** (the controller is a finite state machine):
> - **Passive** - motors limp, robot sits on the ground. startup state.
> - **FixStand** - holds a fixed standing pose.
> - **Velocity** - the RL policy is active and driving the robot from velocity commands.
> - **SitDown** - two-phase sit-down (damp, then interpolate) before returning to Passive.

### 3.1 Overview

**Training policy location** (auto-selected by `parser_policy_dir`):
```
robot_lab/logs/rsl_rl/unitree_b2w_multiexpert/<latest-timestamp>/exported/policy.onnx
```

> **Note**: Run `play.py` to convert from `.pt` to `.onnx` format. 

**IMPORTANT**: Set which policy the controller deploys (for sim2sim or sim2real) by opening `unitree_rl_lab/deploy/robots/b2w/config/config.yaml` and editing `policy_dir` to point at the log root of the run you want.   
`parser_policy_dir` function in controller automatically finds most recent timestamp subdirectory that contains an `exported/` folder and loads `policy.onnx` from it.  
See [Step 2 - Export to ONNX](#44-step-2---export-to-onnx) to generate `.onnx` file from a `.pt` checkpoint.

**Shared deploy config** (loaded by the controller at startup): This is the yaml used when the robot is in Velocity state.
```
unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml  ← observation/action config
```
> Note this has to follow Training damping and stiffness values. Refer to [section 8](#8-b2w-config-verify-before-sim2real).

### 3.2 Prerequisite Installation

These steps are required once on the host machine before the first build.

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

### 3.3 Check this before running sim2sim

#### `unitree_mujoco/simulate/config.yaml`

```yaml
robot: "b2w"
domain_id: 0
interface: "lo"       # loopback for sim2sim
use_joystick: 0       # 0 = no USB gamepad required (keyboard mode)
```

#### MJCF model

Confirm `unitree_mujoco/unitree_robots/b2w/` exists and contains `b2w.xml`.

**Verified actuator order in b2w.xml** (matches training order - no permutation needed):
```
[0]  FR_hip   [1]  FR_thigh  [2]  FR_calf
[3]  FL_hip   [4]  FL_thigh  [5]  FL_calf
[6]  RR_hip   [7]  RR_thigh  [8]  RR_calf
[9]  RL_hip   [10] RL_thigh  [11] RL_calf
[12] FR_foot  [13] FL_foot   [14] RR_foot  [15] RL_foot
```

#### ONNX policy file

After training and play, `policy.onnx` will be at:

```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_multiexpert/<timestamp>/exported/
```

Check that `policy_dir` in
`unitree_rl_lab/deploy/robots/b2w/config/config.yaml` is correct:

```yaml
policy_dir: ../../../../robot_lab/logs/rsl_rl/unitree_b2w_multiexpert
```

### 3.4 Terrain Generation

Mujoco simulator ships with a flat ground scene (`scene.xml`) for each robot. So, use the terrain generator tool to produce a `scene_terrain.xml` that adds obstacles, rough ground, or Perlin heightfields.  

#### Prerequisites (once)

```bash
python3 -m pip install noise opencv-python-headless --break-system-packages
```

> The system Python on Ubuntu 24.04 is externally-managed; `--break-system-packages safe for these small packages.

#### Generate terrain

The following runs the generator and then patches the output:

```bash
cd /workspace/near-locomotion-quadruped/unitree_mujoco/terrain_tool
python3 terrain_generator.py

# Fix the go2 references the generator leaves in the output
sed -i 's/model="go2 scene"/model="b2w scene"/' ../unitree_robots/b2w/scene_terrain.xml
sed -i 's|<include file="go2.xml" />|<include file="b2w.xml"/>|' ../unitree_robots/b2w/scene_terrain.xml
```

<details>
<summary><strong>What should have changed in <code>scene_terrain.xml</code></strong></summary>

After patching, `scene_terrain.xml` should reference `b2w`, not `go2`:

| Line | Before (generator output) | After (patched) |
|---|---|---|
| Scene model name | `model="go2 scene"` | `model="b2w scene"` |
| Robot include | `<include file="go2.xml" />` | `<include file="b2w.xml"/>` |

</details>

#### Switch between flat and terrain scenes

In `unitree_mujoco/simulate/config.yaml`:
```yaml
# Flat ground (default):
robot_scene: "scene.xml"

# Terrain:
robot_scene: "scene_terrain.xml" 
```

Then restart `./unitree_mujoco`.

#### Available terrain functions

<details>
<summary><strong>Click to expand Available terrain functions table</strong></summary>

| Function | Description | Key parameters |
|----------|-------------|----------------|
| `AddRoughGround` | Random cube field | `nums=[N,N]` grid, `box_size`, `box_euler_rand` for tilt |
| `AddPerlinHeighField` | Smooth undulating surface via Perlin noise | `size`, `height_scale`, `smoothness` |
| `AddStairs` | Ascending staircase | `width`, `height`, `stair_nums` |
| `AddSuspendStairs` | Floating stairs with gaps | `gap` |
| `AddBox` | Single box obstacle | `position`, `euler`, `size` |
| `AddGeometry` | sphere, cylinder, capsule, etc. | `geo_type` |
| `AddHeighFieldFromImage` | Terrain from a grayscale image | `input_img`, `height_scale` |

</details>

### 3.5 Switching to Gamepad

To use a physical USB gamepad (or the unitree_mujoco software joystick) instead of keyboard
velocity commands:

**In `b2w/config/deploy.yaml`**:
<details>
<summary><strong>Comment out keyboard_velocity_commands + Uncomment velocity_commands:</strong></summary>

```yaml
observations:
  # Uncomment this:
  velocity_commands:
    params: {command_name: base_velocity}
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

### 3.6 Code Changes Made

#### Shared headers (unitree_rl_lab)

Controller for B2W did not exist in this repo initially, so a duplicate with the same format as B2 and Go2w was created. Changes are backward-compatible and gated so
existing robots (b2, go2, h1, g1_29dof) are unaffected.

##### 1. [`deploy/include/FSM/FSMState.h`](../unitree_rl_lab/deploy/include/FSM/FSMState.h) - keyboard FSM transitions

| Action | Why |
|---|---|
| Added a [`keyboard_transitions` parsing block](../unitree_rl_lab/deploy/include/FSM/FSMState.h#L47-L70) immediately after the existing `transitions` block and before `// register for all states` (code below). | When [`FSMState::keyboard`](../unitree_rl_lab/deploy/include/FSM/FSMState.h#L93) is `nullptr`, the block is skipped. |

<details>
<summary><strong>Click to expand CPP snippet</strong></summary>

```cpp
auto kb_transitions = param::config["FSM"][state_string]["keyboard_transitions"];
if(kb_transitions && keyboard)
{
    auto kb_map = kb_transitions.as<std::map<std::string, std::string>>();
    for(auto it = kb_map.begin(); it != kb_map.end(); ++it)
    {
        std::string target_fsm = it->first;
        if(!FSMStringMap.right.count(target_fsm))
        {
            spdlog::warn("FSM State_'{}' not found in FSMStringMap!", target_fsm);
            continue;
        }
        int fsm_id = FSMStringMap.right.at(target_fsm);
        std::string key_str = it->second;
        registered_checks.emplace_back(
            std::make_pair(
                [key_str]()->bool{ return FSMState::keyboard->on_pressed
                                       && FSMState::keyboard->key() == key_str; },
                fsm_id
            )
        );
    }
}
```

</details>

The `keyboard_transitions` YAML block in `config.yaml` maps target-state name → key string:

```yaml
keyboard_transitions:
  FixStand: "f"
  Passive:  "x"
```

##### 2. [`deploy/include/isaaclab/envs/mdp/observations/observations.h`](../unitree_rl_lab/deploy/include/isaaclab/envs/mdp/observations/observations.h) - wheel-masked joint positions

| Action | Why |
|---|---|
| Added a generic observation [`joint_pos_rel_without_wheel`](../unitree_rl_lab/deploy/include/isaaclab/envs/mdp/observations/observations.h#L90) between `joint_pos_rel` and `joint_vel_rel` (code below); wheel indices are read from `deploy.yaml`. | The B2W policy was trained with `joint_pos_rel_without_wheel`: a 16-element `q - q_default` vector where the four wheel slots [12–15] are forced to 0.0 - wheel is only velocity controlled not position controlled. |

<details>
<summary><strong>Click to expand CPP snippet</strong></summary>

```cpp
// Like joint_pos_rel, but zeroes the slots listed in params["wheel_joint_ids"].
REGISTER_OBSERVATION(joint_pos_rel_without_wheel)
{
    auto & asset = env->robot;
    std::vector<float> data(asset->data.joint_pos.size());
    for (size_t i = 0; i < asset->data.joint_pos.size(); ++i)
        data[i] = asset->data.joint_pos[i] - asset->data.default_joint_pos[i];

    try {
        const auto wheel_ids = params["wheel_joint_ids"].as<std::vector<int>>();
        for (int idx : wheel_ids)
            if (idx >= 0 && idx < static_cast<int>(data.size())) data[idx] = 0.0f;
    } catch (const std::exception &) {}

    return data;
}
```

</details>

The wheel indices are read from `deploy.yaml`:

```yaml
joint_pos_rel_without_wheel:
  params: {wheel_joint_ids: [12, 13, 14, 15]}
```

##### 3. [`deploy/include/FSM/State_SitDown.h`](../unitree_rl_lab/deploy/include/FSM/State_SitDown.h) - implementing SitDown state

| Action | Why |
|---|---|
| New FSM state with two phases, then auto-transitions to Passive. **Phase 1** ([`settle_time`](../unitree_rl_lab/deploy/include/FSM/State_SitDown.h#L22-L23) s): `kp=0`, Passive `kd` - pure damping bleeds momentum from the RL gait. **Phase 2** (`duration` s): linearly interpolates leg joints from the settled pose to the FixStand sit target (`qs[1]`). Wheel joints (`kp=0`) damp to a stop and are skipped from interpolation. | The damping phase lets momentum die out first and interpolation guides the robot down slowly. |

<details>
<summary><strong>Click to expand CPP snippet</strong></summary>

```cpp
// Phase 1: follow actual joint positions under pure damping
for(int i = 0; i < (int)kd_passive_.size(); ++i)
    lowcmd->msg_.motor_cmd()[i].q() = lowstate->msg_.motor_state()[i].q();

// Phase 2: interpolate leg joints toward sit pose.
// Skip joints where kp==0 (wheels) - they just damp to a stop.
float alpha = std::min((float)((t - t_interp_) / duration_), 1.0f);
int   n     = (int)std::min(q0_.size(), sit_q_.size());
for(int i = 0; i < n; ++i)
{
    if(kp_stand_[i] > 0)
        lowcmd->msg_.motor_cmd()[i].q() = q0_[i] + alpha * (sit_q_[i] - q0_[i]);
}
if(alpha >= 1.0f) done_ = true;
```

</details>

`settle_time` and `duration` are configured in `config.yaml`'s `SitDown:` block:

```yaml
SitDown:
  settle_time: 0.05   # seconds of pure-damping before interpolation starts
  duration:    2.5   # seconds for the leg-joint interpolation to the sit pose
```

#### B2W-specific files

`deploy/robots/b2w/` was copied from `deploy/robots/b2/` and extended to support the four wheel joints. The B2 controller handles 12 DOF with pure position PD; B2W adds 4 velocity-controlled wheels on top, which required changes to the config arrays, the control loop, and the observation set. The shared DDS IDL and FSM structure are identical to B2.

##### 4. [`deploy/robots/b2w/config/config.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/config.yaml)

All joint arrays extended from 12 → 16 entries for the wheels. `keyboard_transitions` added to every FSM state. A `SitDown` state added for a graceful sit-down before going limp (absent in b2). `policy_dir` points at the b2w multiexpert log root.

<details>
<summary><strong>Click to expand DIFF snippet</strong></summary>

```diff
 FSM:
   Passive:
+    keyboard_transitions:
+      FixStand: "f"
   FixStand:
-    transitions:
-      Passive: LT + B.on_pressed
-    kp: [400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400]
-    kd: [  8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8]
+    transitions:
+      SitDown: LT + B.on_pressed
+    keyboard_transitions:
+      SitDown: "x"
+      Velocity: "r"
+    kp: [400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 0, 0, 0, 0]
+    kd: [  8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   3,   3,   3,   3]
   Velocity:
+    keyboard_transitions:
+      SitDown: "x"
-    policy_dir: ../../../logs/rsl_rl/unitree_b2_velocity
+    policy_dir: ../../../../robot_lab/logs/rsl_rl/unitree_b2w_multiexpert
+  SitDown:
+    settle_time: 0.05
+    duration: 2.5
```

</details>

##### 5. [`deploy/robots/b2w/main.cpp`](../unitree_rl_lab/deploy/robots/b2w/main.cpp)

[Keyboard initialised](../unitree_rl_lab/deploy/robots/b2w/main.cpp#L9) (b2 leaves it `nullptr`). `State_SitDown` included.

```diff
+#include "FSM/State_SitDown.h"

-std::shared_ptr<Keyboard> FSMState::keyboard = nullptr;
+std::shared_ptr<Keyboard> FSMState::keyboard = std::make_shared<Keyboard>();

```

##### 6. [`deploy/robots/b2w/src/State_RLBase.cpp`](../unitree_rl_lab/deploy/robots/b2w/src/State_RLBase.cpp)

Two additions over b2:

**[`keyboard_velocity_commands` observation](../unitree_rl_lab/deploy/robots/b2w/src/State_RLBase.cpp#L22)** - maps numpad to `[lin_vel_x, lin_vel_y, ang_vel_z]`. Activated in `deploy.yaml` by using `keyboard_velocity_commands` as the observation key instead of `velocity_commands`, replacing the gamepad for sim2sim.

```diff
+REGISTER_OBSERVATION(keyboard_velocity_commands)
+{
+    // w/up/8=fwd, s/down/2=back, a/4=left, d/6=right, q/left/7=yaw-CCW, e/right/9=yaw-CW
+    ...
+}
```

**Hybrid control loop** - b2 sends all joints as position PD; b2w splits into legs `[0,12)` position PD and wheels `[12,16)` velocity control (`kp=0`, [`kd=KD_WHEEL=1.0`](../unitree_rl_lab/deploy/robots/b2w/src/State_RLBase.cpp#L48)). `processed_actions()` already applies `scale=5.0` - do not multiply again.

<details>
<summary><strong>Click to expand DIFF snippet</strong></summary>

```diff
-for(int i(0); i < env->robot->data.joint_ids_map.size(); i++)
-    lowcmd->msg_.motor_cmd()[...].q() = action[i];

+for(int i(0); i < 12; i++)                          // legs: position PD
+    lowcmd->msg_.motor_cmd()[...].q() = action[i];
+
+for(int i(12); i < 16; i++) {                        // wheels: velocity control
+    mc.q()  = 0.0f;  mc.dq() = action[i];
+    mc.kp() = 0.0f;  mc.kd() = KD_WHEEL;  mc.tau() = 0.0f;
+}
```

</details>

**`deploy.yaml` path** changed from per-run `params/deploy.yaml` (b2) to the shared `config/deploy.yaml`.

```diff
-YAML::LoadFile(policy_dir / "params" / "deploy.yaml")
+YAML::LoadFile(param::config_dir / "deploy.yaml")
```

##### 7. [`deploy/robots/b2w/config/deploy.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml) - NEW (does not exist in b2)

RobotLab training runs save their Isaac Lab/RSL-RL configs under each run's `params/` folder as
`env.yaml` and `agent.yaml`; they do **not** generate `deploy.yaml`.

`deploy.yaml` belongs to the separate `unitree_rl_lab` deployment stack. It is the hand-written
adapter that lets the Unitree C++ controller run a RobotLab repo trained B2W policy by recreating the
same runtime interface the policy saw during training: observation order, command inputs, joint
mapping, action scaling, leg PD gains, wheel velocity control, and B2W-specific wheel observation
handling.

For B2W this file is centralised at:

```text
unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml
```

The B2W deploy controller loads this shared config directly instead of looking for a per-policy
`params/deploy.yaml`. Key B2W additions:

```diff
+keyboard_velocity_commands:   # replaces velocity_commands - keyboard drives the policy
+joint_pos_rel_without_wheel:  # replaces joint_pos_rel - zeroes wheel slots [12-15]
+  params: {wheel_joint_ids: [12, 13, 14, 15]}
+joint_ids_map: [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]  # identity; MJCF order matches training
+# wheel slots [12-15]: stiffness=0.0, damping=1.0
```

**Policy observation vector (57 elements total):**
```
base_ang_vel              ×3   (scale 0.25)
projected_gravity         ×3   (scale 1.0)
keyboard_velocity_commands×3   (scale 1.0)
joint_pos_rel_wo_wheel    ×16  (scale 1.0, wheel slots = 0)
joint_vel_rel             ×16  (scale 0.05)
last_action               ×16  (scale 1.0)
```

> **Critical:** every observation term must have `history_length: 1` (not 0).
> With `history_length: 0` the internal ring buffer discards every sample immediately →
> the observation vector fed to ONNX is empty → ONNX reads past the buffer → segfault on the first policy step.
> All six terms in `deploy.yaml` already have `history_length: 1` - do not change them to 0.

---

## 4. Workflow

Train a locomotion policy in Isaac Lab, watch it in the Isaac Sim GUI, export it to ONNX, and validate it in MuJoCo sim2sim.

### 4.1 Step 1 - Train Teacher in Isaac Lab

Open a terminal and set up the Isaac Lab Python environment first. Each terrain expert is trained as its own teacher - run the command for the expert you want.

**The following example is for training Teacher Policy:**
```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0 \
  --headless --max_iterations 5000   # without --max_iterations it runs for 20000 iterations
```
For other experts replace the `task` flag with:  
**Slope Up teacher**: `RobotLab-Isaac-Velocity-SlopeUp-Teacher-Unitree-B2W-v0`  


<details>
<summary><strong>Training with wandb logging</strong></summary>

**1. Install wandb and log in** (once):
```bash
/isaac-sim/python.sh -m pip install wandb
wandb login
```

**2. Train with wandb flags:**
```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless --max_iterations 5000 \
  --logger wandb \
  --log_project_name b2w-rough-v1
```

Runs log to `wandb.ai` under the project `b2w-rough-v1`. Each run is named after its timestamp directory automatically.

**3. Resume into the same wandb run:**

Find the run ID:
```bash
ls /workspace/near-locomotion-quadruped/robot_lab/wandb/
# format: run-<datetime>-<ID>  ← ID is the part after the last hyphen
```

Then resume (`max_iterations` is additive - if you checkpointed at iteration 400 and want to reach 5000 total, pass 4600):
```bash
WANDB_RUN_ID=<run-id> WANDB_RESUME=allow \
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1 \
  --headless --max_iterations <remaining_iterations> \
  --logger wandb \
  --log_project_name b2w-rough-v1 \
  --resume \
  --load_run <timestamp>
```
</details>

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

Checkpoints are saved per teacher experiment:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_staircaseup_teacher/<timestamp>/
```

### 4.2 Step 1b - Watch the Robot Walk in Isaac Sim

Use `play.py` to load a checkpoint, watch the robot in the Isaac Sim GUI, and export the policy. This script is for normal visual playback, not the controlled evaluation matrix. Key flags:

- `--task` - environment to load (same as training, unless you are intentionally testing actor-only transfer).
- `--load_run <timestamp>` - load a specific run; omit to auto-load the most recent.
- `--num_envs 1` - spawn a single robot; omit for multiple parallel environments (no keyboard then).
- `--keyboard` - steer interactively. Drives `base_velocity` from the keyboard (velocity tasks).
- `--load_actor_only` - load only the actor and skip critic weights. Use this when the actor observation space matches but the critic observation space differs between tasks.

#### Run play.py with keyboard control

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --load_run 2026-05-24_05-47-04 \
  --num_envs 1 \
  --keyboard
```

> Remove `--load_run` to auto-load the most recent run, or omit `--num_envs 1` to spawn multiple parallel environments. Keyboard mode is meant for one robot so the commands are easy to inspect.

#### Keyboard controls

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

> **Verify each expert before distillation.** Do not start distillation until you have visually confirmed that every teacher actually performs its skill well - a weak teacher distils into a weak student. Check each expert in **both** environments:
> - **Isaac Sim** - the `play.py` run above; watch the teacher climb/ascend its terrain cleanly under keyboard control.
> - **MuJoCo sim2sim** - follow [Section 4.6 - Sim2Sim in MuJoCo](#46-step-3---sim2sim-in-mujoco) to confirm the same behaviour survives the sim2sim transfer.
>
> If a teacher is timid, drifts, or falls, tweak its rewards and retrain before distilling. See [Section 5 - Curriculum Training with Different Terrain](#5-curriculum-training-with-different-terrain) (e.g. [5.5 Worked example: StaircaseUp teacher](#55-worked-example-staircaseup-teacher)) for exactly which rewards were tuned and why.


### 4.3 Step 1c - Distillation (Student-Teacher)

Distillation produces a deployable student policy that uses only proprioceptive observations (no height scan, no linear velocity). Student learns to mimic it via MSE loss on its own on-policy rollouts.

#### Phase 1 - Train the teachers (PPO)

The teachers are the privileged PPO policies already trained in [Step 1](#41-step-1---train-teacher-in-isaac-lab) - the StaircaseUp expert and the SlopeUp expert in this case. Make sure each one has been visually verified (see the note at the end of [Section 4.2](#42-step-1b---watch-the-robot-walk-in-isaac-sim)) before distilling.

#### Phase 2 - Multi-Expert Distillation

Multi-expert distillation distils **several** terrain experts (e.g. StaircaseUp + SlopeUp) into **one** student in a single run. All experts are listed in [`teachers.txt`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/teachers.txt); the combined environment is built from them and each robot is taught by the expert matching its terrain.

> **Check `teachers.txt` first.** Before training, open [`teachers.txt`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/teachers.txt) and confirm it lists exactly the experts you want, each pointing at the correct (visually-verified) teacher checkpoint. The combined environment is built straight from this file - a wrong or stale entry silently distils the wrong teacher.

The student here is an **LSTM** (recurrent), not an **MLP** (feed-forward).   

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --headless
```

No `--load_run` is needed here. Teacher checkpoints come from `teachers.txt`.  
Students land in `logs/rsl_rl/unitree_b2w_multiexpert/`. How `teachers.txt` is parsed and the code behind it is in [Section 5.6 - Multi-Expert Terrain](#56-multi-expert-terrain); scoring the student on each teacher's terrain is in [Section 4.5](#45-step-2a---evaluate-policies-per-level-evaluation-csv).

<details>
<summary><strong>Code Changes (LSTM student cfg)</strong></summary>
**File:** `.../config/wheeled/unitree_b2w/agents/rsl_rl_distillation_cfg.py`

**File:** `.../config/wheeled/unitree_b2w/agents/rsl_rl_distillation_cfg.py`

- New file added: ` /workspace/near-locomotion-quadruped/robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/agents/rsl_rl_distillation_cfg.py `
- New RNN class added: `UnitreeB2WRoughDistillationRunnerRecurrentCfg`: student switched from `RslRlMLPModelCfg` to `RslRlRNNModelCfg` (`rnn_type="lstm"`, `rnn_hidden_dim=256`, `rnn_num_layers=1`). Teacher and `obs_groups` inherited unchanged.
- Added an `algorithm` override on that class: `gradient_length=24` (was 15) and `max_grad_norm=1.0` (was unset).

> This file was built ontop of Anymal_D student training code.
> Under: `/workspace/near-locomotion-quadruped/robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/quadruped/anymal_d/agents/rsl_rl_distillation_cfg.py`

**File:** `.../config/wheeled/unitree_b2w/__init__.py`

- Registered `rsl_rl_distillation_recurrent_cfg_entry_point` → `UnitreeB2WRoughDistillationRunnerRecurrentCfg` on the rough task.
</details>


#### Phase 3 - Visually verify the student in Isaac Sim

Before exporting, watch the distilled student drive in the Isaac Sim GUI. Use the same task and recurrent agent as training, and steer it with the keyboard:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --num_envs 1 \
  --keyboard
```

Omit `--load_run` to auto-load the most recent `unitree_b2w_multiexpert` run. Drive it with the numpad keys from [Section 4.2](#42-step-1b---watch-the-robot-walk-in-isaac-sim) and confirm the single student handles every teacher's terrain cleanly.

> **Run headless instead.** Add `--headless` (and drop `--num_envs 1 --keyboard`) to run without opening a window - useful on a remote box or when you only want to trigger the ONNX export:
> ```bash
> python scripts/reinforcement_learning/rsl_rl/play.py \
>   --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
>   --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
>   --headless
> ```


### 4.4 Step 2 - Export to ONNX

Running `play.py` auto-exports `policy.onnx` into an `exported/` subfolder next to the loaded checkpoint.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --headless
```
> Can **Ctrl+C** if it runs successfully without crashing.
> The `--agent` flag loads the recurrent (LSTM) distillation student; without it, `play.py` would try to load the multiexpert checkpoint as a plain PPO actor.

<details>
<summary><strong>Export from a specific run</strong></summary>

```bash
setup_isaaclab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --headless \
  --load_run 2026-05-24_05-47-04
```
</details>

The exported policy will be at:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_multiexpert/<timestamp>/exported/policy.onnx
```

### 4.5 Step 2a - Evaluate Policies (Per-Level Evaluation CSV)

Once you have more than one trained policy, use the orchestrator in `scripts/evaluation/evaluation.py`. Give it policy experiment names, run folders, or checkpoint paths, and it resolves the newest checkpoint from `logs/rsl_rl/`.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/evaluation/evaluation.py \
  --policies unitree_b2w_slopeup_teacher unitree_b2w_staircaseup_teacher \
  --headless
```

The orchestrator calls `eval_worker.py` for each compatible policy/terrain pair and writes one row per terrain level, plus a collapsed `<out_csv>_summary.csv` matrix with one summative success rate per terrain. See [Section 6](#6-evaluation-matrix) for the full command, dynamic policy lookup, success metric, and CSV columns. By default the evaluation is done at 0.9*maximum training diffculty.

For normal use, call `scripts/evaluation/evaluation.py` instead of `eval_worker.py` directly. The orchestrator fills in the task ids, policy labels, terrain labels, level count, robot count, duration, and output CSV for you.

#### Evaluate a multi-expert student on the teachers' terrains

To score a multi-expert student (from [Section 4.3](#43-step-1c---distillation-student-teacher)) on each terrain it was distilled from, pass the student to `--policies` and the teacher terrains to `--terrain`:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/evaluation/evaluation.py \
  --policies unitree_b2w_multiexpert \
  --terrain staircaseup_teacher slopeup_teacher \
  --headless
```

`--terrain` forces every policy to be run on every listed terrain (otherwise terrains are inferred from the policy name). Valid `--terrain` keys are the [`KNOWN_TERRAINS`](../robot_lab/scripts/evaluation/evaluation.py) keys, e.g. `flat`, `rough`, `staircaseup_teacher`, `slopeup_teacher`.

> The `unitree_b2w_multiexpert` checkpoint is a **distillation** checkpoint (it stores `student_state_dict`, not `actor_state_dict`). [`evaluation.py`](../robot_lab/scripts/evaluation/evaluation.py) maps that experiment to the distillation agent entry point automatically, so the deployable LSTM student is loaded and scored - no extra flags needed.


### 4.6 Step 3 - Sim2Sim in MuJoCo

> **Verify config first.** Before this sim2sim run, confirm the B2W physical parameters, gains, scales, and observation layout match across all configs - see [§8. B2W Config (Verify Before Sim2Real)](#8-b2w-config-verify-before-sim2real). A mismatch here is the most common cause of a policy that walks in Isaac Sim but falls in MuJoCo.

Run the exported ONNX policy against the MuJoCo simulator over DDS on loopback.
No physical robot or gamepad required - control is via keyboard.

> **First time only:** complete the one-time setup, build, and `simulate/config.yaml` config
> under [MuJoCo Sim2Sim Validation Setup](#3-mujoco-sim2sim-validation-setup) - system packages, `unitree_sdk2`,
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
| 3 | `r` | Policy activates (Velocity mode) |
| 4 | Numpad `8` / `2` / `4` / `6` | Forward / backward / strafe left / right |
| 5 | Numpad `7` / `9` | Yaw CCW / CW |
| 6 | `x` | Return to sitdown |

</details>

Velocity commands use the numpad keys (`8`/`2`/`4`/`6`) plus `7`/`9` for yaw - the same mapping as the §4.2 keyboard-controls table. (`keyboard_velocity_commands` in the controller only maps these numpad digits.)

> Pressing `x` returns the robot to Passive - it slowly sits down and goes limp.

#### Replicability - deploying a new trained policy

The sim2sim infrastructure (simulator, controller binary, config) never changes between
training runs. `b2w_ctrl` auto-selects the newest run: `parser_policy_dir` sorts all
timestamp directories under `policy_dir` and picks the last one that contains `exported/`.

**No manual file copying is needed.** `deploy.yaml` is no longer stored inside each policy's
`params/` folder - it lives at a single canonical location:

```
unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml
```

The controller loads it from there on every startup. After training and exporting a new
policy, just start `./b2w_ctrl --network lo` as normal - it picks up the new `policy.onnx`
automatically and reads `deploy.yaml` from `config/`.

> No rebuild needed here, as just tweaking yaml file. Latest .onnx file from the logs/<task> will be obtained.

### 4.7 Step 3b - Generate rough terrain

Check how to set it up under [B2W MuJoCo Sim2Sim Validation → Terrain Generation](#34-terrain-generation).

> The terrain generator supports: rough ground (random cubes), Perlin heightfield, stairs,
> floating stairs, arbitrary boxes and geometry.

---

### 4.8 Step 4 - Sim2Real (to be tested)

> **Verify config first.** Before running on the real robot, walk the full checklist in [§8. B2W Config (Verify Before Sim2Real)](#8-b2w-config-verify-before-sim2real) and confirm every value matches the [official `unitree_ros` B2W URDF](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/b2w_description).

Following are the steps to deploy the multiexpert student policy
(`robot_lab/logs/rsl_rl/unitree_b2w_multiexpert`) onto the real robot

The controller binary, `deploy.yaml`, and FSM are **identical to sim2sim** - the same `b2w_ctrl`
you already ran against MuJoCo. Only two things change for hardware:

1. `policy_dir` in `config.yaml` points at the multiexpert student log root.
2. `b2w_ctrl` runs on the robot's real network interface instead of `lo`.


The E-Stop Button is **X** on the laptop, after deploying the policy.

#### Prerequisites

- `b2w_ctrl` already builds and runs cleanly in [sim2sim](#46-step-3---sim2sim-in-mujoco) (so the
  controller, `unitree_sdk2`, and the ONNX Runtime symlink are all set up).
- The physical B2W is powered on and sitting on the ground. It does not need to be put in any
  special low-level mode - the controller claims the motor channel on startup, and `f` stands it up.

#### 1. Export the multiexpert student policy to ONNX

To deploy onto the robot, need `.onnx` format file.
See [Step 2 - Export to ONNX](#44-step-2---export-to-onnx) for details.

#### 2. Confirm the controller points at the multiexpert student logs

In [`unitree_rl_lab/deploy/robots/b2w/config/config.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/config.yaml),
`policy_dir` under the `Velocity` state should be the multiexpert student log root:

```yaml
  Velocity:
    policy_dir: ../../../../robot_lab/logs/rsl_rl/unitree_b2w_multiexpert
```

`parser_policy_dir()` goes down the folder and auto-selects the newest timestamp dir containing an
`exported/` folder.

#### 3. Connect and configure networking

Follow the steps listed in the documentation: https://support.unitree.com/home/en/B2_developer/Quick%20Start

#### 4. Run the controller

```bash
sim2sim_env
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/robots/b2w
./build/b2w_ctrl --network eth0
```

> source `sim2sim_env` for sim2real as well.


#### Operating sequence

Identical to sim2sim. Keep the controller's terminal focused for keyboard input.

<details>
<summary><strong>Click to expand table</strong></summary>

| Step | Key | Result |
|------|-----|--------|
| 1 | *(wait)* | Robot limp in Passive |
| 2 | `f` | Stands up (FixStand, ~3 s) |
| 3 | `r` | Policy engages (Velocity mode) |
| 4 | Numpad `8` / `2` / `4` / `6` | Forward / backward / strafe left / right |
| 5 | Numpad `7` / `9` | Yaw CCW / CW |
| 6 | `x` | E-stop: graceful sit-down → Passive |

</details>

> If you are driving from the wireless remote instead of the keyboard, `LT + B` triggers the same
> graceful sit-down (the `Velocity → SitDown` transition in `config.yaml`).

#### Hardware gain tuning

If standing feels sluggish or the robot wobbles, the gains to adjust (no rebuild needed - YAML is
read each time you enter `Velocity`):

| Gain | Where | Default | Notes |
|---|---|---|---|
| Leg stiffness / damping (Velocity) | [`deploy.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml) `stiffness`/`damping` [0-11] | `160` / `5` | Raise stiffness if sluggish; lower if motors buzz |
| Wheel damping (Velocity) | `deploy.yaml` `damping` [12-15] | `1.0` | Mirrors `KD_WHEEL`; raise if wheels chatter or drift at rest |
| Leg hold gains (FixStand) | [`config.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/config.yaml) `FixStand.kp`/`kd` | `400` / `8` | Wheel slots [12-15] are `kp=0` here - see [§9.1](#91-fixstand-wheel-skid---bug-that-passed-in-sim-but-failed-on-the-real-robot) |

`KD_WHEEL` in [`State_RLBase.cpp`](../unitree_rl_lab/deploy/robots/b2w/src/State_RLBase.cpp) is
compile-time; changing it (rather than the `deploy.yaml` wheel damping) requires a rebuild.

These defaults mirror the B2W training articulation config in
[`unitree.py`](../robot_lab/source/robot_lab/robot_lab/assets/unitree.py) (the `UNITREE_B2W_CFG`
actuators: legs `stiffness=160` / `damping=5`, wheels `stiffness=0` / `damping=1.0`), which in
turn references Unitree's published robot models at
[unitreerobotics/unitree_ros](https://github.com/unitreerobotics/unitree_ros) (as noted in the
header of `unitree.py`).

#### Restoring factory control

Stop `b2w_ctrl` with `Ctrl+C`, then restart the robot. 

#### Onboard (untethered) deployment

To run untethered, the controller runs on the Jetson itself and you drive with the wireless remote;
the ethernet tether is only needed up front to build and launch.

1. Over the tether, SSH into the Jetson (`192.168.123.164`) and build there. The x86_64 workstation
   binary will not run on the Jetson's ARM64, so rebuild `unitree_sdk2` and `b2w_ctrl` on the
   Jetson, and copy the `unitree_b2w_multiexpert` log dir across so `policy_dir` resolves locally.
2. Launch on the Jetson with `--network <jetson NIC on 192.168.123.0/24>`. Once it is running the
   tether can be unplugged - the controller lives entirely on the robot.
3. Drive with the wireless remote instead of the keyboard: switch the velocity observation from
   keyboard to gamepad as in [Switching to Gamepad](#35-switching-to-gamepad). The FSM transitions
   (FixStand / Velocity / SitDown) already work from the gamepad buttons.


---

## 5. Curriculum Training with Different Terrain

Every B2W terrain policy uses **velocity tracking** (the robot is told a forward/sideways/turning speed and rewarded for matching it). What you vary between policies is the **terrain** - the obstacles the robot trains on (stairs, slopes, boxes, rough ground, ...), see [5.4](#54-plug-in-a-different-terrain).

The default `v0` task is **mixed rough terrain + velocity tracking**. To build a new variant you swap the terrain ([5.4](#54-plug-in-a-different-terrain)). Section [5.5](#55-worked-example-staircaseup-teacher) shows the same recipe filled in for the StaircaseUp teacher.

All training runs in Isaac-Sim with 4096 parallel environments. Sections [5.2](#52-sub-terrains-the-default-mix) and [5.3](#53-terrain-difficulty-curriculum) explain how the default terrain and its difficulty curriculum work - read them once as background before building your own variant.

### 5.1 Training Command

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0
```

---

### 5.2 Sub-Terrains (the default mix)

The default `v0` terrain is a grid of tiles built from `ROUGH_TERRAINS_CFG` (defined in `isaaclab/terrains/config/rough.py`). Six terrain types are mixed together, each taking a proportion of the columns:

<details>
<summary><strong>Click to expand table</strong></summary>

| Terrain Type | Proportion | Difficulty Parameter | Description |
|---|---|---|---|
| `pyramid_stairs` | 20% | step height: 5 cm → 23 cm | Ascending pyramid of steps - robot must climb up and over |
| `pyramid_stairs_inv` | 20% | step height: 5 cm → 23 cm | Descending inverted pyramid - robot must step down into a pit |
| `boxes` | 20% | box height: 5 cm → 20 cm | Grid of randomly-sized raised blocks spread across the tile |
| `random_rough` | 20% | noise amplitude: 2 cm → 10 cm | Heightfield with random uniform noise - uneven bumpy ground |
| `hf_pyramid_slope` | 10% | slope angle: 0° → ~22° | Smooth pyramid ramp - robot must navigate a continuous slope |
| `hf_pyramid_slope_inv` | 10% | slope angle: 0° → ~22° | Inverted smooth pyramid - robot must descend into a concave slope |

</details>

Each tile is **8 m × 8 m**. The full terrain grid is **10 rows × 20 columns**, giving 200 tiles in total. The difficulty parameter for each terrain type scales **linearly from its minimum to its maximum** across the 10 rows - row 0 has the easiest version of each terrain, row 9 has the hardest.

**4096 parallel environments** run simultaneously in simulation, collecting experience in parallel each step. This gives a large, diverse batch of transitions for each policy update.

---

### 5.3 Terrain Difficulty Curriculum

Training does **not** use random terrain placement. Instead, a progressive curriculum is used so the robot develops skills on easier terrain before being exposed to harder terrain.

#### How the curriculum is enabled

In `velocity_env_cfg.py`, the `CurriculumCfg` includes a `terrain_levels` term:

```python
terrain_levels = CurrTerm(func=mdp.terrain_levels_vel)
```

When this term is present (not `None`), the environment automatically sets:

```python
self.scene.terrain.terrain_generator.curriculum = True
```

This tells the terrain generator to arrange tiles in **ascending order of difficulty across rows** rather than randomly. Row 0 of every terrain type uses the minimum difficulty parameter; row 9 uses the maximum.

#### Initial placement

At the start of training, each of the 4096 environments is assigned a **random starting level between 0 and 5** (inclusive):

```python
# terrain_importer.py
self.terrain_levels = torch.randint(0, max_init_level + 1, (num_envs,), device=self.device)
```

`max_init_terrain_level = 5` (for `rough_env_cfg.py` only) is set in the scene config, so no robot starts on the hardest half of the terrain grid. The upper levels (6–9) are unlocked only through earned progression during training.

#### Progression and regression at each episode end

At the end of every episode, `terrain_levels_vel` evaluates **each environment independently** by measuring how far the robot physically travelled from its spawn point:

```python
# curriculums.py
distance = torch.norm(asset.data.root_pos_w[env_ids, :2] - env.scene.env_origins[env_ids, :2], dim=1)

move_up   = distance > terrain.cfg.terrain_generator.size[0] / 2   # walked > 4 m → promote
move_down = distance < torch.norm(command[env_ids, :2], dim=1) * max_episode_length_s * 0.5
```

- **Promote** (`move_up`): the robot walked more than 4 m - it successfully navigated the terrain. Its level increases by 1.
- **Demote** (`move_down`): the robot walked less than 50% of what the commanded velocity required - it struggled. Its level decreases by 1.
- **No change**: performance was in between.

This judgment is made for all 4096 envs simultaneously using vectorised tensor operations - no loop over individual robots.

#### Spawning at the new level

After levels are updated, `update_env_origins` teleports each robot to the tile at its new difficulty level on the next reset:

<details>
<summary><strong>Click to expand PYTHON snippet</strong></summary>

```python
# terrain_importer.py
self.terrain_levels[env_ids] += 1 * move_up - 1 * move_down

# floor at 0, and if a robot exceeds the max level it is sent to a random level
self.terrain_levels[env_ids] = torch.where(
    self.terrain_levels[env_ids] >= self.max_terrain_level,
    torch.randint_like(self.terrain_levels[env_ids], self.max_terrain_level),
    torch.clip(self.terrain_levels[env_ids], 0),
)

self.env_origins[env_ids] = self.terrain_origins[self.terrain_levels[env_ids], self.terrain_types[env_ids]]
```

</details>

A robot that beats the hardest level (row 9) is sent to a **random level** rather than back to level 0, ensuring it continues to see a variety of difficulties.

#### Summary of the full training loop

<details>
<summary><strong>Click to expand Summary of the full training loop snippet</strong></summary>

```
Initialisation
  └─ Each of 4096 envs assigned random terrain level 0–5

Every episode step
  └─ Actor observes robot state → outputs joint targets
  └─ Critic estimates value of current state
  └─ PPO uses critic values to compute advantages → updates actor & critic weights

Every episode end (per env, vectorised)
  └─ Measure distance travelled from spawn
  └─ terrain_levels[i] += 1  (if move_up)
  └─ terrain_levels[i] -= 1  (if move_down, floored at 0)
  └─ env_origins[i] = terrain tile at new level
  └─ Robot resets at new tile on next episode
```

</details>

Because each env tracks its own level independently, the 4096-env population naturally **spreads across the full difficulty range** over time. Early in training most envs sit at low levels; as the policy improves the distribution shifts toward higher levels.

#### Velocity command curriculum (disabled for B2W)

The framework also supports a separate curriculum that starts the commanded velocity range at 10% of maximum and widens it as the tracking reward improves. For the B2W task this is explicitly disabled:

```python
# rough_env_cfg.py
self.curriculum.command_levels_lin_vel = None
self.curriculum.command_levels_ang_vel = None
```

The B2W robot is therefore commanded to track velocities from the full range (`±1 m/s` linear, `±1 rad/s` angular) from the very first episode. Only the terrain difficulty is gated by the curriculum.

---

### 5.4 Plug in a different terrain

A terrain variant is just a new `TerrainGeneratorCfg` wired into a subclass of the `rough-env-v0`.  
Don't edit `v0`, instead create a parallel env cfg that follows the same format, with different terrain and reward system (if needed).

#### First, pick your terrain configs

All terrain configs are importable via `import isaaclab.terrains as terrain_gen` and live in two files:

| File | What's in it |
|---|---|
| `isaaclab/terrains/trimesh/mesh_terrains_cfg.py` | Solid 3D mesh configs (`Mesh*`) |
| `isaaclab/terrains/height_field/hf_terrains_cfg.py` | Heightfield surface configs (`Hf*`) |

Full paths from the repo root:
```
/workspace/isaaclab/source/isaaclab/isaaclab/terrains/trimesh/mesh_terrains_cfg.py
/workspace/isaaclab/source/isaaclab/isaaclab/terrains/height_field/hf_terrains_cfg.py
```

The actual geometry generation functions (useful for understanding what each terrain looks like) are in the sibling `*_terrains.py` files in the same directories.

**Trimesh (`Mesh*`) - solid 3D geometry, robot can fall off edges:**

- Use for real gaps, pits, rails, boxes, and other obstacles with sharp geometry.
- Use `MeshInvertedPyramidStairsTerrainCfg` for the staircase-up teacher.
- Key knobs: `step_height_range`, `step_width`, `platform_width`, obstacle size/depth/gap ranges.

**Heightfield (`Hf*`) - continuous surface sampled on a grid:**

- Use for rough ground, slopes, waves, stairs, and grid-sampled obstacle fields.
- Use `HfInvertedPyramidStairsTerrainCfg` for the staircase-up teacher.
- Key knobs: `slope_range`, `step_height_range`, `step_width`, `platform_width`, `noise_range`.

> **Mesh vs Hf:** Mesh terrains are solid trimesh geometry - robots fall into real voids. Heightfield terrains are a continuous surface with no actual holes (except `HfSteppingStonesTerrainCfg`, which uses `holes_depth=-10` to fake deep pits).

---

#### Then, wire it up in four files

**Step 1 - Choose the terrain composition.** Pick the terrain types and the proportion each takes (must sum to 1.0). For each type, set the difficulty range: the value at row 0 (easiest) and at row 9 (hardest). The tables above list the key difficulty parameter per type.

**Step 2 - Add the env config.** Create `<task>_env_cfg.py` next to [`rough_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/rough_env_cfg.py). Define a fresh `TerrainGeneratorCfg` (never mutate `ROUGH_TERRAINS_CFG` - it is shared by `v0`), subclass `UnitreeB2WRoughEnvCfg`, and swap in the new generator in `__post_init__`. Re-apply the two guards the parent gates on its own class name:

<details>
<summary><strong>Click to expand template snippet</strong></summary>

```python
import isaaclab.terrains as terrain_gen
from isaaclab.terrains import TerrainGeneratorCfg
from isaaclab.utils import configclass
from .rough_env_cfg import UnitreeB2WRoughEnvCfg

MY_TERRAINS_CFG = TerrainGeneratorCfg(
    size=(8.0, 8.0), border_width=20.0, num_rows=10, num_cols=20,
    horizontal_scale=0.1, vertical_scale=0.005, slope_threshold=0.75,
    use_cache=False,
    sub_terrains={
        # add your chosen terrain types here
    },
)

@configclass
class UnitreeB2W<task>EnvCfg(UnitreeB2WRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.terrain.terrain_generator = MY_TERRAINS_CFG
        # re-apply curriculum flag - parent sets it on the old generator before the swap
        if getattr(self.curriculum, "terrain_levels", None) is not None:
            self.scene.terrain.terrain_generator.curriculum = True
        # re-run zero-weight reward pruning - parent gates it on its own class name
        if self.__class__.__name__ == "UnitreeB2W<task>EnvCfg":
            self.disable_zero_weight_rewards()
```

> **Note on `gpu_collision_stack_size`:** terrains with many discrete surfaces (stepping stones, gap, repeated objects) generate far more collision contacts than smooth terrains. If you see `PhysX error: collisionStackSize buffer overflow` at runtime, add `self.sim.physx.gpu_collision_stack_size = 2**27` to `__post_init__` to raise the GPU buffer from the default 64 MB to 128 MB.

</details>

**Step 3 - Add a PPO runner config.** Append to [`rsl_rl_ppo_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/agents/rsl_rl_ppo_cfg.py) so the variant logs to its own directory:

```python
@configclass
class UnitreeB2W<task>PPORunnerCfg(UnitreeB2WRoughPPORunnerCfg):
    def __post_init__(self):
        super().__post_init__()
        self.experiment_name = "unitree_b2w_<task>"
```

**Step 4 - Register the gym task id.** Add a `gym.register(...)` block to [`__init__.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/__init__.py):

<details>
<summary><strong>Click to expand PYTHON snippet</strong></summary>

```python
gym.register(
    id="RobotLab-Isaac-Velocity-<Task>-Unitree-B2W",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": f"{__name__}.<task>_env_cfg:UnitreeB2W<task>EnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UnitreeB2W<task>PPORunnerCfg",
    },
)
```

</details>

Train it with `--task=RobotLab-Isaac-Velocity-<Task>-Unitree-B2W`. All existing tasks stay untouched.

---

### 5.5 Worked example: StaircaseUp teacher

This example follows the same four steps from [Section 5.4](#54-plug-in-a-different-terrain), but fills them in for a velocity-based StaircaseUp teacher.

The task stays inside the velocity folder:

```text
robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/
```

The registered task is:

```text
RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0
```

This is a **velocity tracking** task: the robot is asked to follow forward/sideways/turning speed commands.

#### Step 1 - Choose the terrain composition

The terrain is defined in:

```text
staircaseup_teacher_env_cfg.py
```

The config creates a new `STAIRCASEUP_TEACHER_CFG` instead of editing the shared rough terrain. It uses only upward staircase terrain:

| Terrain piece | Share | What it gives the robot |
|---|---:|---|
| `MeshInvertedPyramidStairsTerrainCfg` | 50% | sharp, solid stair edges |
| `HfInvertedPyramidStairsTerrainCfg` | 50% | smoother heightfield stairs |

Both use step heights from **6 cm to 20 cm** with a fixed 27.5 cm tread, centred on the real hanger staircase (16.8 cm rise, 27.8 cm step width). Every tile here is an ascending staircase.

#### Step 2 - Add the env config

`UnitreeB2WStaircaseUpTeacherEnvCfg` subclasses the normal B2W rough velocity config:

```python
class UnitreeB2WStaircaseUpTeacherEnvCfg(UnitreeB2WRoughEnvCfg):
```

Inside `__post_init__`, it makes the staircase task different from the default rough task:

| Change | Why |
|---|---|
| `self.scene.terrain.terrain_generator = STAIRCASEUP_TEACHER_CFG` | use the staircase-only terrain |
| `self.sim.physx.gpu_collision_stack_size = 2**27` | give PhysX more room for many stair contacts |
| `curriculum = True` on the new terrain generator | keep the row-by-row difficulty curriculum from 5.3 |
| `self.scene.terrain.max_init_terrain_level = 0` | start on the easiest stair row |

Then it keeps velocity tracking but tunes the rewards for climbing:

| Reward change | Plain meaning |
|---|---|
| `track_lin_vel_xy_exp: 3.0 -> 5.0` | reward forward/sideways speed tracking more |
| `track_ang_vel_z_exp: 1.5 -> 2.5` | reward turning speed tracking more |
| `action_rate_l2: -0.01 -> -0.0025` | allow quicker leg motions |
| `joint_pos_penalty: -1.0 -> -0.25` | allow bigger leg bends on stairs |
| `lin_vel_z_l2: -2.0 -> -0.5` | allow the body to rise when climbing |
| `feet_height_body: 0 -> -2.0` | encourage higher foot/wheel clearance |

**Raising the rewards** (`track_lin_vel_xy_exp` 3.0 → 5.0, `track_ang_vel_z_exp` 1.5 → 2.5) so moving beats standing still.  
**Relaxing the penalties** that fight climbing (`action_rate_l2`, `joint_pos_penalty`, `lin_vel_z_l2`) so the robot can take quicker, bigger leg motions and let its body rise onto a step.  
Turning on `feet_height_body` (0 → -2.0) lifts the feet/wheels higher to clear taller steps.  
Everything else (episode length, curriculum promotion, `upward`) is inherited unchanged from the rough task.

Finally, it reruns `disable_zero_weight_rewards()` for this subclass, because the parent only does that automatically for its own base class name.

#### Step 3 - Add a PPO runner config

The runner config is added in:

```text
agents/rsl_rl_ppo_cfg.py
```

It subclasses the normal B2W rough PPO settings and only changes the experiment name:

```python
class UnitreeB2WStaircaseUpTeacherPPORunnerCfg(UnitreeB2WRoughPPORunnerCfg):
    def __post_init__(self):
        super().__post_init__()
        self.experiment_name = "unitree_b2w_staircaseup_teacher"
```

This keeps the training algorithm the same while saving logs and checkpoints under a separate run folder.

#### Step 4 - Register the gym task id

The task is registered in:

```text
__init__.py
```

The registration connects the task name to the two new config classes:

```python
gym.register(
    id="RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": f"{__name__}.staircaseup_teacher_env_cfg:UnitreeB2WStaircaseUpTeacherEnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UnitreeB2WStaircaseUpTeacherPPORunnerCfg",
    },
)
```

Train it with:

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0
```

In short: this teacher does not introduce a new reward style. It uses the same velocity tracking idea as the rough task, but trains on staircase-only terrain and relaxes the penalties that would otherwise make climbing too cautious.


### 5.6 Multi-Expert Terrain

The teachers in 5.5 each cover **one** terrain. A multi-expert run merges several of those experts into **one** combined environment and distils them into **one** deployable LSTM student. Each robot trains on the terrain it spawns on and is copied (behavior-cloned) by the matching expert - the per-env routing from *Parkour in the Wild*. The result: no forgetting, a single run, and one student that handles every terrain at once.

#### `teachers.txt` drives the whole thing

The experts are listed in [`teachers.txt`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/teachers.txt), one per line. The **line index is the expert id**:

```
# task_id                                                    expert_PPO_checkpoint
RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0  /abs/.../unitree_b2w_staircaseup_teacher/
RobotLab-Isaac-Velocity-SlopeUp-Teacher-Unitree-B2W-v0      /abs/.../unitree_b2w_slopeup_teacher/
```

- `task_id` - the per-teacher task (from 5.4 / 5.5). Its terrain is pulled in and merged into the combined env.
- `expert_PPO_checkpoint` - that expert's trained PPO checkpoint, loaded as its teacher (newest `model_*.pt` is auto-picked from a run folder).
- optional third column - a per-expert `weight` (default `1.0`) that sets its share of terrain columns.

At startup the combined env reads the file, merges every expert's sub-terrains into one curriculum terrain, and computes a **column → expert** map (using the terrain generator's deterministic column formula) so each robot is supervised by the expert for the terrain it stands on. **Add an expert = add a line** - the terrain and routing reshape automatically.

Train it as shown in [Section 4.3](#43-step-1c---distillation-student-teacher); students land in `logs/rsl_rl/unitree_b2w_multiexpert/`. Score the student per terrain in [Section 4.5](#45-step-2a---evaluate-policies-per-level-evaluation-csv).

<details>
<summary><strong>Multi-expert training - code changes</strong></summary>

Four new files, **no `train.py` edit**. The combined env auto-shapes from `teachers.txt`.

1. [`multiexpert_teacher_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/multiexpert_teacher_env_cfg.py) - reads `teachers.txt`, merges each listed task's sub-terrains into one curriculum terrain, precomputes the column → expert map, and stores the checkpoint paths + map on the cfg for the algorithm to read.
2. [`mdp/distillation/multiteacher.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py) (+ [`__init__.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/__init__.py)) - `MultiTeacherDistillation`, a subclass of RSL-RL `Distillation`. It loads N frozen teachers, routes supervision per env in `act()`, and saves `student_state_dict` plus a per-expert `teacher_<i>_state_dict`.
3. [`agents/rsl_rl_multiexpert_distillation_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/agents/rsl_rl_multiexpert_distillation_cfg.py) - reuses the recurrent (LSTM) runner cfg from [Section 4.3](#43-step-1c---distillation-student-teacher) and only swaps the algorithm `class_name` to `MultiTeacherDistillation`; `experiment_name = unitree_b2w_multiexpert`.
4. [`__init__.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/__init__.py) - registers `RobotLab-Isaac-Velocity-MultiExpert-Teacher-Unitree-B2W-v0`.

> No `train.py` edit is needed: the stock single-checkpoint load only fires when `algorithm.class_name == "Distillation"`. Here it is the dotted `MultiTeacherDistillation` path, so that branch is skipped and `--load_run` is not required.

</details>

<details>
<summary><strong>Sim2sim of the recurrent student - code changes</strong></summary>

The distilled student is an **LSTM**, so it is stateful. `play.py` exports an ONNX graph with hidden-state I/O (`h_in`/`c_in` in, `h_out`/`c_out` out), not just `obs → actions`. The stock C++ runner ([`OrtRunner`](../unitree_rl_lab/deploy/include/isaaclab/algorithms/algorithms.h)) expects a stateless MLP and aborts on activation:

```
what(): Input name h_in not found in observations.
```

Fix (b2w-local, shared deploy library untouched):

- New [`RecurrentOrtRunner.h`](../unitree_rl_lab/deploy/robots/b2w/include/RecurrentOrtRunner.h) - detects carry-over state from the graph by the rsl-rl `<x>_in` / `<x>_out` naming (MLP → 0 pairs, GRU → 1, LSTM → 2), seeds the hidden state to zero, feeds `*_in`, and carries `*_out` forward each step. Backward compatible: a stateless MLP finds 0 pairs and behaves exactly like the stock runner, so the rough/teacher policies still deploy unchanged.
- One construction line in [`State_RLBase.cpp`](../unitree_rl_lab/deploy/robots/b2w/src/State_RLBase.cpp) switches the runner to it.

Then rebuild `b2w_ctrl` and run sim2sim as in [Section 4.6](#46-step-3---sim2sim-in-mujoco).

</details>


## 6. Evaluation Matrix

The evaluation entry point is `scripts/evaluation/evaluation.py`. It is an orchestrator around `eval_worker.py`: the orchestrator finds checkpoints and decides which tasks to run, while `eval_worker.py` owns the Isaac rollout.

You can pass full paths, run folders, experiment folders, or just experiment names. If an experiment name is not a path, the orchestrator looks under:

```text
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/
```

For example, `unitree_b2w_slopeup_teacher` resolves to the newest `model_<N>.pt` under `logs/rsl_rl/unitree_b2w_slopeup_teacher/`. (The orchestrator looks for the worker at `scripts/evaluation/eval_worker.py`.)

### 6.1 Command

Run from `robot_lab`:

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/evaluation/evaluation.py \
  --policies unitree_b2w_slopeup_teacher unitree_b2w_staircaseup_teacher \
  --headless
```

Equivalent path-based usage is also valid:

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/evaluation/evaluation.py \
  --policies \
  /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_staircaseup_teacher/2026-06-11_03-52-37 \
  /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_slopeup_teacher \
  --headless
```

Useful options:

| Option | Meaning |
|---|---|
| `--policies` | Experiment names under `logs/rsl_rl/`, run folders, experiment folders, or direct `model_*.pt` paths |
| `--out_csv` | Output CSV path; default is `evaluation.csv` |
| `--levels` | Number of terrain levels to test; default is `9` |
| `--robots_per_level` | Number of robots spawned on each level; default is `512` |
| `--duration_s` | Optional rollout length. If omitted, it is chosen from both terrain and robot count. At `512` robots per level, every terrain (StaircaseUp/SlopeUp included) uses `20s`. |
| `--headless` | Passes headless mode through to `eval_worker.py`. If omitted, the Isaac window can be shown so you can watch the evaluation. |

### 6.2 How it picks terrains

The orchestrator reads the experiment name and maps it to a registered Isaac task.

Known examples:

| Experiment name | Family | Terrain | Task used |
|---|---|---|---|
| `unitree_b2w_slopeup_teacher` | velocity | `SlopeUp` | `RobotLab-Isaac-Velocity-SlopeUp-Teacher-Unitree-B2W-v0` |
| `unitree_b2w_staircaseup_teacher` | velocity | `StaircaseUp` | `RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0` |
| `unitree_b2w_flat` | velocity | `Flat` | `RobotLab-Isaac-Velocity-Flat-Unitree-B2W-v0` |
| `unitree_b2w_rough` | velocity | `Rough` | `RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0` |
| `unitree_b2w_rough_v1` | velocity | `RoughV1` | `RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1` |

Each policy is cross-evaluated on the velocity terrains inferred from the policy list.

### 6.3 Evaluation Settings

`evaluation.py` uses `eval_worker.py` internally to make each rollout a controlled, repeatable measurement:

- Robots start upright with zero reset velocity.
- The per-step level-progression curriculum is disabled (robots are not promoted or demoted mid-eval), but the terrain generator's `curriculum=True` ordering is enabled, so each row is a fixed, monotonically increasing difficulty. The per-level rows therefore actually mean increasing difficulty (before, rows were randomly difficult).
- Difficulty across the level rows is set by `EVAL_DIFFICULTY_RANGE` (default `(0.9, 0.9)`), where `1.0` is the hardest terrain seen in training. With the low and high both at `0.9`, every row runs at a fixed `0.9` of the trained max - just below the hardest training terrain. (Raising the high end above `1.0` would extrapolate the terrain parameters *beyond* training - taller steps, steeper slopes, with no clamp.)
- The terrain keeps its trained column layout. For the B2W SlopeUp/StaircaseUp teacher terrains, this means `num_cols=20`; `512` robots per level are distributed across those columns instead of creating `512` terrain columns.
- Velocity tasks use a fixed command by default: `x=0.6`, `y=0.0`, `yaw=0.0`.
- Velocity tasks honour `--duration_s`/`--eval_duration_s` for the rollout length. The per-level CSV's `duration_s` records the length actually run.

**Success metric.** A robot succeeds if it walked at least `EVAL_TRAVERSE_FRACTION` of the terrain size from its spawn (default 0.5, i.e. ~4 m on the 8 m B2W terrains) **and** never fell. This mirrors the training curriculum's "cleared the terrain" threshold (`terrain_levels_vel`).

> Why not just survival? A "did-not-fall" metric is traversal-blind: a robot that stalls at the bottom of a staircase pit stays upright and would count as a success at *any* step height, hiding the difficulty. Requiring real forward progress means harder terrain actually lowers the score.

**Tuning knobs (macros in `eval_worker.py`).** These are intentionally module-level constants, not CLI flags, so the evaluation surface stays fixed and reproducible:

| Macro | Default | Meaning |
|---|---|---|
| `EVAL_DIFFICULTY_RANGE` | `(0.9, 0.9)` | Low/high difficulty fraction across the level rows; `>1.0` would be beyond training |
| `EVAL_TRAVERSE_FRACTION` | `0.5` | Velocity-task success: fraction of terrain size the robot must walk from spawn (0.5 = ~4 m) |

> difficulty 0.9  -> 0.04 + 0.9 * (0.30 - 0.04)  
>                 -> 0.04 + 0.234  
>                 -> 0.274 m  

### 6.4 What the CSV Records

The orchestrator launches `eval_worker.py` once per compatible `(policy, terrain)` pair. `eval_worker.py` places robots evenly across terrain levels and writes **two** CSVs per run.

**Per-level CSV** (`--out_csv`, default `evaluation.csv`) - one row per terrain difficulty level:

| Column | Meaning |
|---|---|
| `policy` | Policy label, usually the experiment name without `unitree_b2w_` |
| `terrain` | Terrain label, such as `StaircaseUp` or `SlopeUp` |
| `terrain_level` | Difficulty level, written as `1` through `9` |
| `difficulty` | Difficulty fraction of that level (e.g. `0.90`); `>1.0` would be beyond training |
| `cleared` | Number of robots that succeeded on that level (distance-traverse) |
| `total` | Number of robots tested on that level |
| `success_rate` | `cleared / total` |
| `duration_s` | Rollout length used for that result |
| `checkpoint` | Exact checkpoint used |
| `task` | Registered Isaac task id used for that terrain |

**Summary CSV** (sibling `<out_csv>_summary.csv`, e.g. `evaluation_summary.csv`) - the difficulty levels collapsed into a single summative success rate per `(terrain, policy)`. This accumulates into a terrain x policy matrix (rows = terrain; columns = `<policy>_success` and `<policy>_level`), in the style of *Parkour in the Wild* Table 4. The same matrix is also printed to stdout as markdown.

The summary success rate is:

```text
summary_success_rate(policy, terrain)
  = sum(cleared over all tested levels) / sum(total over all tested levels)
```

With the default `9` levels and `512` robots per level:

```text
summary_success_rate = (cleared_1 + cleared_2 + ... + cleared_9) / (512 * 9)
```

> Note: the summative rate is a flat average over every robot in the sweep. With the default `EVAL_DIFFICULTY_RANGE=(0.9, 0.9)` every level row runs at a fixed `0.9` of the trained max, so the single number reflects performance just below the hardest training terrain.

### 6.5 Files and Reasoning

**Orchestrator:** `scripts/evaluation/evaluation.py`

1. This is the command you run.
2. It does not start Isaac Sim by itself.
3. It finds the checkpoint for each policy name you pass.
4. It decides which terrain task matches each policy.
5. It calls `eval_worker.py` once for each compatible `(policy, terrain)` pair.
6. This keeps the command simple: you can pass names like `unitree_b2w_slopeup_teacher` instead of full checkpoint paths.

**Evaluation worker:** `scripts/evaluation/eval_worker.py`

1. This file starts Isaac Sim.
2. It loads one policy checkpoint.
3. It runs the policy on one terrain task.
4. It places robots evenly across terrain levels so each CSV row has a clear difficulty.
5. It starts robots upright and still, so the result is not dominated by random bad resets.
6. It uses fixed commands, so the climbing test is not mixed with random sideways, backward, or turning commands.
7. It keeps the trained terrain column layout. For example, `512` robots per level means many samples on the same terrain layout, not a new 512-column terrain.
8. It can load only the actor, which helps when a policy is tested on another compatible task whose critic observation shape is different.
9. It writes both the per-level CSV rows and the collapsed summary row.

**Normal play/export:** `scripts/reinforcement_learning/rsl_rl/play.py`

1. Use this file when you want to watch a policy.
2. Use it when you want keyboard control.
3. Use it when you want to export `policy.onnx` or `policy.pt`.
4. It does not force the strict evaluation setup above.
5. This keeps play mode useful for visual inspection, while `evaluation.py` is used for evaluating policies on different terrain.

Relevant `play.py` behavior:

1. `--keyboard` drives the velocity command by setting `base_velocity` from the keyboard for velocity tasks.
2. `--load_actor_only` skips critic weights when you intentionally load an actor into a task whose critic observation size differs.
3. Normal play reduces generated terrain rows/columns to save memory.
4. Normal play disables curriculum and random pushes, which makes the GUI easier to inspect.


## 7. Skills Trained On

This section tracks which skills the policy has been trained on and which are planned next.

### 7.1 Successfully trained on

#### Teacher Policies  
The following are the expert policies that have been extensively trained for about 5000 iterations on specific tasks:
| Policy | Terrain | Notes |
|---|---|---|
| **Rough** (`unitree_b2w_rough`, the default `v0` task) | Mixed rough terrain (stairs, boxes, rough ground, slopes) | The general-purpose baseline policy. |
| **StaircaseUp teacher** (`unitree_b2w_staircaseup_teacher`) | Upward staircases only (step height 6 cm → 20 cm, step width 27.5 cm) | Specialised stair-climbing teacher - see the worked example in [5.5](#55-worked-example-staircaseup-teacher). |
| **SlopeUp teacher** (`unitree_b2w_slopeup_teacher`) | Upward slopes only (slope 0.0 → 0.50 rad, i.e. 0° → ~28.6°) | Specialised slope-climbing teacher; steeper than the rough task's ~22° slopes. |

> **Real-stair sim2real note:** the StaircaseUp curriculum is tuned to the physical staircase in the hanger - step height **16.8 ± 0.3 cm** and step width **27.8 ± 0.4 cm**. The terrain (`staircaseup_teacher_env_cfg.py`) uses a step-height range of 6-20 cm and a fixed 27.5 cm tread, so the real rise lands near the top of the curriculum with a small margin above it, and the trained tread is slightly narrower than reality (marginally harder in sim than on the real stairs).

#### Student Policies   
Student policy exists at `/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_student`  
The student was trained through the following method:

#### Performance Table  

Success rate (%) per terrain. Columns are the evaluated policies; rows are the test terrains.

| Terrain | $\pi_{slope}$ | $\pi_{stair}$ | $\pi_{student}$ |
|---|---|---|---|
| SlopeUp | 98.9 | 63.1 | 92.1 |
| StaircaseUp | 8.2 | 99.6 | 92.9 |

### 7.2 What we want to train on next

All of the following reuse the existing velocity env (`RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0`) and need **config-only changes** - no new task definitions or algorithms.

<details>
<summary><strong>Click to expand table</strong></summary>

| Skill | How | Why useful |
|---|---|---|
| **Flat high-speed driving** | Already registered: `RobotLab-Isaac-Velocity-Flat-Unitree-B2W-v0`. Widen `commands.base_velocity.ranges.lin_vel_x` (the commented `(-2.0, 2.0)` lines in `rough_env_cfg.py`) | Exploits the wheels - fast, efficient rolling that legs-only robots can't do |
| **Stair / curb / slope climbing** | Bias the terrain generator toward stairs + pyramids + gaps and let the terrain curriculum ramp difficulty | The headline wheeled-legged advantage: roll on flat, *step* over obstacles |
| **Rock-solid stand-still (no drift)** | Increase the `stand_still` reward weight in `rough_env_cfg.py` + zero-command holding | Directly targets command-following drift at zero command - useful as its own objective |
| **Payload robustness / push recovery** | Base + link mass are already randomized in `rough_env_cfg.py`; add external-force push events and heavier payload ranges | Carrying loads + surviving shoves = real-world deployment readiness |
| **Energy-efficient locomotion** | Raise `joint_power` / `wheel_vel_penalty` reward weights | Minimizes cost-of-transport → battery life |
| **Gait shaping** (trot/pace, or wheel-vs-step mode) | `feet_gait`, `feet_air_time` rewards (currently `feet_gait.weight = 0`) | Cleaner, more natural or task-specific gaits |
| **Posture / ride-height control** | `base_height_l2` target height | Crouch under obstacles, raise to clear |

</details>

## 8. B2W Config (Verify Before Sim2Real)

Before deploying onto the real robot, confirm the B2W's physical parameters agree across **every** config in the pipeline (training asset -> training env -> deploy -> MuJoCo). The single source of truth is the official Unitree description: [`unitree_ros/robots/b2w_description`](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/b2w_description). All values below were cross-checked against that URDF and `unitree.py` on 2026-06-17.

### 8.1 Source of Truth - `unitree.py`

The training asset [`UNITREE_B2W_CFG`](../robot_lab/source/robot_lab/robot_lab/assets/unitree.py#L248-L320) defines the actuator limits, PD gains, and default pose that every downstream config must match:

```python
init_state=ArticulationCfg.InitialStateCfg(
    pos=(0.0, 0.0, 0.65),
    joint_pos={
        ".*L_hip_joint": 0.0,
        ".*R_hip_joint": -0.0,
        "F.*_thigh_joint": 0.8,
        "R.*_thigh_joint": 0.8,
        ".*_calf_joint": -1.5,
        ".*_foot_joint": 0.0,
    },
    joint_vel={".*": 0.0},
),
soft_joint_pos_limit_factor=0.9,
actuators={
    "hip": DCMotorCfg(
        joint_names_expr=[".*_hip_joint"],
        effort_limit=200.0, saturation_effort=200.0, velocity_limit=23.0,
        stiffness=160.0, damping=5.0, friction=0.0,
    ),
    "thigh": DCMotorCfg(
        joint_names_expr=[".*_thigh_joint"],
        effort_limit=200.0, saturation_effort=200.0, velocity_limit=23.0,
        stiffness=160.0, damping=5.0, friction=0.0,
    ),
    "calf": DCMotorCfg(
        joint_names_expr=[".*_calf_joint"],
        effort_limit=320.0, saturation_effort=320.0, velocity_limit=14.0,
        stiffness=160.0, damping=5.0, friction=0.0,
    ),
    "wheel": ImplicitActuatorCfg(
        joint_names_expr=[".*_foot_joint"],
        effort_limit_sim=20.0, velocity_limit_sim=50.0,
        stiffness=0.0, damping=1.0, friction=0.0,
    ),
},
```

**Confirmed identical** to the [`unitree_ros` B2W URDF](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/b2w_description) (checked 2026-06-17):

| Joint | Range (rad) [URDF] | Effort N·m [URDF] | Velocity rad/s [URDF] | `unitree.py` effort / sat / vel | Match |
|---|---|---|---|---|---|
| hip | -0.87, 0.87 | 200 | 23 | 200 / 200 / 23 | ✅ |
| thigh | -0.94, 4.69 | 200 | 23 | 200 / 200 / 23 | ✅ |
| calf | -2.82, -0.43 | 320 | 14 | 320 / 320 / 14 | ✅ |
| foot (wheel) | continuous | 20 | 50 | 20 / - / 50 | ✅ |

> The `stiffness`/`damping` (legs `160`/`5`, wheels `0`/`1`) are **control gains**, not part of the URDF. They live in `unitree.py` and must be mirrored in `deploy.yaml` - see the checklist below.

### 8.2 Checklist - Verify Before Sim2Real

Walk these six files top-to-bottom and confirm each matches the source of truth above. Each row links to the file to check.

| # | File | Verify |
|---|---|---|
| 1 | [`unitree.py`](../robot_lab/source/robot_lab/robot_lab/assets/unitree.py#L248-L320) `UNITREE_B2W_CFG` | effort / saturation / velocity limits match the URDF table (§8.1); leg `stiffness=160`, `damping=5`; wheel `stiffness=0`, `damping=1`; default pose `hip=0, thigh=0.8, calf=-1.5, wheel=0` |
| 2 | [`rough_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/rough_env_cfg.py#L99-L106) | action scales `hip=0.125`, `thigh/calf=0.25`, `wheel=5.0`; obs scales `base_ang_vel=0.25`, `joint_vel=0.05`; `base_lin_vel` and `height_scan` set to `None` (policy is blind) |
| 3 | [`deploy.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml) | leg `stiffness=160` / `damping=5`, wheel `kp=0` / `kd=1`; `default_joint_pos` = §8.1 pose; action `scale`/`offset` = row 2; observation order + scales; `step_dt: 0.02` (= sim dt `0.005` × decimation `4`) |
| 4 | [`config.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/config.yaml) | FixStand **hold** gains `kp=400` / `kd=8` (intentionally stiffer than the policy gains - hold only, not the RL gains); stand pose `qs`; `policy_dir` -> `unitree_b2w_multiexpert` |
| 5 | [`b2w.xml`](../unitree_mujoco/unitree_robots/b2w/b2w.xml) | joint `range` = URDF; actuator `ctrlrange` hip/thigh `±200`, calf `±320`, wheel `±20`; wheel `ref` (set to `0` for the nominal robot - a non-zero `ref` injects the FixStand wheel-skid repro, see [§9.1](#91-fixstand-wheel-skid---bug-that-passed-in-sim-but-failed-on-the-real-robot)) |
| 6 | [`config.yaml` (MuJoCo)](../unitree_mujoco/simulate/config.yaml) | `robot: "b2w"`; `interface: "lo"` for sim2sim; `use_joystick: 0` for keyboard |

> **Gain sources differ by FSM state - this is intentional.** FixStand (row 4) uses a stiff `kp=400/kd=8` position hold to stand the robot up. The Velocity (RL) state uses `kp=160/kd=5` from `deploy.yaml` (row 3), matching the training asset. Do not "reconcile" these two - they are different controllers.

### 8.3 DCMotor Speed-Torque Matching in MuJoCo

<details>
<summary><b>Why the MuJoCo bridge now clamps leg torque by joint speed (B2W only)</b></summary>

**Symptom.** The B2W climbed stairs cleanly in Isaac Sim but in MuJoCo sim2sim the legs were over-aggressive - the robot rushed the stairs and struggled to climb. Flat ground looked fine in both. Same policy, same controller, so the gap was in the simulator, not the policy.

**Root cause - mismatched actuator models.** The B2W legs are trained with [`DCMotorCfg`](../robot_lab/source/robot_lab/robot_lab/assets/unitree.py#L285-L311) (§8.1), which models a real BLDC motor's speed-torque envelope: as a joint speeds up, the torque it can produce rolls off toward zero (back-EMF). Isaac Lab applies this every step:

```
τ_max =  saturation_effort · (1 − q̇ / velocity_limit)   clamped to [0, effort_limit]
τ_min =  saturation_effort · (−1 − q̇ / velocity_limit)  clamped to [−effort_limit, 0]
τ     =  clip(τ_pd, τ_min, τ_max)
```

MuJoCo's `<motor>` actuator has **no such rolloff** - it is an idealised torque source with only a constant `ctrlrange` clamp (`±200/±320`). The bridge ([`unitree_sdk2_bridge.h`](../unitree_mujoco/simulate/src/unitree_sdk2_bridge.h)) computed plain PD torque and wrote it straight to `ctrl[i]`. So during fast leg swings on stairs the MuJoCo legs delivered far more torque than the policy ever saw in training (and more than the real motor can), producing the over-driven motion. On flat ground joint speeds are low, the rolloff barely engages, and both sims agree - which is why only stairs exposed it.

This is the same reason go2w transfers without this fix: go2w trains with `ImplicitActuatorCfg` (plain clamped PD = what the bridge already did), so its training and sim2sim actuator models already agree. B2W's `DCMotorCfg` did not.

**Fix (Option A - make MuJoCo match training, no retrain).** The bridge now reproduces the DCMotor envelope for the B2W leg joints before writing `ctrl[i]`. See `apply_dcmotor_limit()` and the PD loop in [`unitree_sdk2_bridge.h`](../unitree_mujoco/simulate/src/unitree_sdk2_bridge.h):

```cpp
double tau = m.tau()
           + m.kp() * (m.q()  - mj_data_->sensordata[i])
           + m.kd() * (m.dq() - joint_vel);
mj_data_->ctrl[i] = apply_dcmotor_limit(i, tau, joint_vel);   // B2W legs only; no-op otherwise
```

- **Scoped to B2W legs.** The helper returns the torque unchanged unless `robot == "b2w"` and the joint is a leg (index `[0,12)`). Wheels (`ImplicitActuatorCfg`) and every other robot are untouched.
- **Parameters mirror §8.1.** hip/thigh: `saturation_effort=effort_limit=200`, `velocity_limit=23`; calf: `320`, `velocity_limit=14`. If you ever change these in `unitree.py`, change them here too - they must stay in lockstep.

**Why Option A and not retraining with `ImplicitActuatorCfg` (Option B)?** Option B would make the two sims agree, but on the *optimistic* model - the policy would learn torque the real motor cannot deliver, reintroducing the same gap on hardware. The real motor has the rolloff (via physics), so keeping `DCMotorCfg` in training and mirroring it in MuJoCo keeps the whole chain (Isaac → MuJoCo → real) consistent. Validity depends on `saturation_effort`/`velocity_limit` matching the real B2 datasheet - they are cross-checked against the URDF in §8.1.

> **Note - the Python bridge is not patched.** This repo's sim2sim path uses the C++ simulator (§3.2). The mirror file [`simulate_python/unitree_sdk2py_bridge.py`](../unitree_mujoco/simulate_python/unitree_sdk2py_bridge.py) still does plain PD; apply the same clamp there if you switch to the Python simulator.

</details>

---

## 9. Challenges Faced

### 9.1 FixStand wheel skid - bug that passed in sim but failed on the real robot

**Challenge.** On the physical B2W, pressing `f` (FixStand / stand-up) made the wheels spin fast
and the robot skid backward. The exact same policy and controller ran cleanly in MuJoCo
sim2sim - the robot stood up normally - so the bug was invisible in simulation and only showed
up on hardware.

**Root cause.** FixStand applies position PD to *all 16 motors*, wheels included
(`kp=400` for every slot in [`config/config.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/config.yaml)).
In [`State_FixStand.h`](../unitree_rl_lab/deploy/include/FSM/State_FixStand.h), `enter()` captures
each wheel's *current* angle as the interpolation start and `run()` drives it to a fixed target
of `0.0` rad. But the wheels are continuously-spinning joints - holding them to an absolute angle
is meaningless. Whatever nonzero angle the wheel encoder happens to read at stand-up becomes a
position error that `kp=400` slams to zero, spinning the wheels and skidding the robot.

The reason sim hid it: `mj_resetData` ([`main.cc`](../unitree_mujoco/simulate/src/main.cc)) starts
every MuJoCo wheel at `qpos = 0`, which already equals FixStand's target → zero position error →
no motion. A real robot's wheel encoders read a nonzero accumulated angle, so the error - and the
skid - is real. The sim simply never exercised the failing condition.

**Solution.**

1. **Reproduce it deterministically in sim first.** Add a `ref` offset to the four wheel joints in
   [`b2w.xml`](../unitree_mujoco/unitree_robots/b2w/b2w.xml) (`ref="50"`, marked
   `REPRO(FixStand wheel skid)`). `ref` sets `qpos0`, so `mj_resetData` starts each wheel at the
   offset angle - mimicking a real encoder reading a large accumulated angle - while the wheel still
   *renders* in its normal position. Running sim2sim and pressing `f` then reproduces the backward
   skid, confirming the diagnosis before touching the real robot. Set `ref` back to `0` to disable.

   > **Why the offset has to be large.** The wheel motors clamp at ±20 Nm
   > ([`b2w.xml`](../unitree_mujoco/unitree_robots/b2w/b2w.xml) `ctrlrange="-20 20"`), so with
   > `kp=400` the torque already saturates at only `20/400 = 0.05 rad` of error. The offset's
   > *magnitude* therefore doesn't change the peak torque - it sets **how long** the wheel is driven
   > at max torque (i.e. how far it has to spin to reach 0). A small offset like `6.28` (one
   > revolution) gives just a brief lurch that then settles; `50 rad` keeps the wheel saturated
   > through the stand-up so the robot skids the entire time and never stands - matching the
   > hardware failure. Tune this value to dial the severity.

2. **Fix the gains.** Set the FixStand `kp` for the wheel slots (indices 12-15) to `0` in
   `config/config.yaml`, so FixStand damps the wheels (`kd` only) instead of position-holding them.
   This matches the intent already noted in that file's comment, and the same `kp=0` hybrid scheme
   the Velocity/RL state uses for the wheels - the wheels coast to a stop on stand-up instead of
   being yanked to an absolute angle.

## 10. Deriving π in RL

### 10.1 Defining Q-function

$$R_t = r_t + \gamma r_{t+1} + \gamma^2 r_{t+2} + \ldots$$

Total reward, $R_t$, is the discounted sum of all rewards obtained from time $t$. $\gamma$ is the discount factor that basically just means future reward not as "rewarding" as current reward.

$$Q(s_t, a_t) = \mathbb{E}[R_t \mid s_t, a_t]$$

Q-function captures the expected total future reward an agent in state $s$ can receive by executing a certain action, $a$.

Ultimately the agent needs a **policy** $\mathbf{\pi(s)}$, to infer the **best possible action** to take at its state $s$. [i.e. choose the action that maximises future reward]

$$\pi^*(s) = \underset{a}{\arg\max}\, Q(s,a)$$

---

## 11. Proximal Policy Optimisation: PPO (Teacher)

PPO is an on-policy actor-critic policy gradient method. *(called **Proximal** because new policy is kept in the **proximity** of the old one)*

- The **actor** is a stochastic policy $\pi_\theta(a \mid s)$.
- The **critic** $V_\phi(s)$ estimates the state value.

Given that the probability ratio between candidate and data-collecting policies:

$$r_t(\theta) = \frac{\pi_\theta(a_t \mid s_t)}{\pi_{\theta_{old}}(a_t \mid s_t)}$$

### 11.1 Hyperparameters

Every PPO hyperparameter referenced below is defined in one file,
`robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/agents/rsl_rl_ppo_cfg.py`
(class `UnitreeB2WRoughPPORunnerCfg`).

<details>
<summary><strong>Click to expand table</strong></summary>

| Parameter | Value | File | Belongs to |
|---|---|---|---|
| `init_noise_std` | `1.0` | `rsl_rl_ppo_cfg.py` | Policy (actor) - initial action std $\sigma$ |
| `num_steps_per_env` | `24` | `rsl_rl_ppo_cfg.py` | Rollout - steps collected per env per iteration |
| `num_learning_epochs` | `5` | `rsl_rl_ppo_cfg.py` | Update loop - epochs over the (stale) batch |
| `num_mini_batches` | `4` | `rsl_rl_ppo_cfg.py` | Update loop - minibatches per epoch |
| `clip_param` | `0.2` | `rsl_rl_ppo_cfg.py` | [Clipped Surrogate Objective](#113-clipped-surrogate-objective) ($\varepsilon$); also clips the [Value Loss](#114-value-critic-loss) |
| `value_loss_coef` | `1.0` | `rsl_rl_ppo_cfg.py` | [Value (Critic) Loss](#114-value-critic-loss) - coefficient $c_v$ in the [combined loss](#112-the-combined-ppo-loss) |
| `use_clipped_value_loss` | `True` | `rsl_rl_ppo_cfg.py` | [Value (Critic) Loss](#114-value-critic-loss) - enables the pessimistic clipped critic loss |
| `entropy_coef` | `0.01` | `rsl_rl_ppo_cfg.py` | [Entropy Bonus](#115-entropy-bonus) - coefficient $c_e$ in the [combined loss](#112-the-combined-ppo-loss) |
| `gamma` | `0.99` | `rsl_rl_ppo_cfg.py` | [GAE](#116-generalised-advantage-estimation-gae) - reward discount $\gamma$ |
| `lam` | `0.95` | `rsl_rl_ppo_cfg.py` | [GAE](#116-generalised-advantage-estimation-gae) - baseline-trust factor $\lambda$ |
| `learning_rate` | `1.0e-3` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#117-adaptive-kl-based-learning-rate-schedule) - initial LR |
| `schedule` | `"adaptive"` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#117-adaptive-kl-based-learning-rate-schedule) |
| `desired_kl` | `0.01` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#117-adaptive-kl-based-learning-rate-schedule) - target KL per update |
| `max_grad_norm` | `1.0` | `rsl_rl_ppo_cfg.py` | [Applying the gradients](#119-applying-the-gradients) - gradient-norm clip |

</details>

> **NOTE:** $\gamma$ is the reward discount, while $\lambda$ separately controls how much the value baseline is trusted.

### 11.2 The Combined PPO Loss

**The combined PPO loss** is implemented verbatim in the RSL-RL source as:

```python
loss = surrogate_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy.mean()
```

$$L = L^{\text{policy}} + c_v\, L^V - c_e\, H(\pi_\theta).$$

The coefficient $c_v$ is `value_loss_coef` and $c_e$ is `entropy_coef` (see [Hyperparameters](#111-hyperparameters)).

### 11.3 Clipped Surrogate Objective

**Clipped Surrogate Objective** is:

$$L^{CLIP}(\theta) = \widehat{\mathbb{E}}_t\left[\min\left(\underbrace{r_t(\theta)\widehat{A}_t}_{unclipped},\ \underbrace{\mathrm{clip}(r_t(\theta), 1-\varepsilon, 1+\varepsilon)\widehat{A}_t}_{clipped}\right)\right]$$

CLIP is asking how far I can trust this batch of data to tell me how to change the policy. This is done by basically:

1. Clip the ratio $r_t(\theta)$ to be between $[1-\varepsilon,\ 1+\varepsilon]$

2. When $r_t(\theta)$ is within the range of $[1-\varepsilon,\ 1+\varepsilon]$, min seems redundant. BUT, if it is just the clipping $[\mathrm{clip}(r_t(\theta), 1-\varepsilon, 1+\varepsilon)\widehat{A}_t]$, gradient is zero.
   Zero gradient tells the "optimizer to stop caring about this sample."
   - If it is **good**, it does not matter, as its already doing a good job.
   - It it is **bad**, it is not correcting the issue.

3. $\widehat{A}_t$ is the advantage estimate (not true $A$) at timestep $t$. It is the sign-and-magnitude signal that tells the update which direction to push.
   - **Case 1a: Good Action**: $\widehat{A}_t > 0$, gain is capped at $r_t = 1 + \varepsilon$
     - Say $r_t = 1.2$, $\varepsilon = 0.2$.
     - So $clipped = 1.2\widehat{A}_t$ and $unclipped = 1.5\widehat{A}_t$
     - min picks $1.2\widehat{A}_t$, and the objective is stuck at this, flat and zero gradient.
       No further reward for pushing the probability higher.
   - **Case 1b: Good Action** but the update went wrong way (i.e. clip is useless here)
     - Say $r_t = 0.5$, $\varepsilon = 0.2$. The action had positive advantage ($\widehat{A}_t > 0$), so we *wanted* $r_t$ to go above 1, but the update pushed it the other way down to 0.5.
     - $unclipped = 0.5\widehat{A}_t$ and $clipped = 0.8\widehat{A}_t$ (0.5 is below the floor of $[0.8, 1.2]$, so it is clamped to 0.8).
     - Since $\widehat{A}_t > 0$, both terms are positive, but $0.5\widehat{A}_t < 0.8\widehat{A}_t$, so min picks $0.5\widehat{A}_t$ (the unclipped one).
     - This gives a non-zero gradient that pushes $r_t$ back up toward 1 - i.e., it corrects the wrong-way update by incentivising the policy to increase the action's probability again.
   - **Bad Action**: When $\widehat{A}_t < 0$, ratio is floored at $r_t = 1 - \varepsilon$.
     - Suppose the update overshoots and drives $r_t$ down to $0.5$.
     - Unclipped: $0.5 \times \widehat{A}_t$ (a negative number, since $\widehat{A}_t < 0$). Clipped: $0.8 \times \widehat{A}_t$ (clamped to $1 - \epsilon = 0.8$, also negative).
     - With $\widehat{A}_t$ negative, $0.8\widehat{A}_t$ is more negative (smaller) than $0.5\widehat{A}_t$. So clip is chosen here to correct the action.

Here $\varepsilon$ is `clip_param` (see [Hyperparameters](#111-hyperparameters)).

> **NOTE:** "Wrong way" = the action's probability moved *opposite* to what its advantage called for.

**$r_t > 1$** means that the new policy assigns **higher probability to that specific action** than the old policy did. **$\widehat{A}_t > 0$** means that the **action turned out to be better than expected**, and you should do more often.

So the order is:
1. **Rollout** - Run the policy, collect states, actions, rewards
2. **Compute** $\widehat{A}_t$ - using GAE over that rollout (fixed for whole update)
3. **Update** - repeatedly adjust $\theta$, which changes $\pi_\theta$ and therefore $r_t$, with $\widehat{A}_t$ as the fixed signal telling each action whether to go up or down

|  | Advantage | Want | "Wrong way" if… |
| --- | --- | --- | --- |
| Good Action | $\widehat{A}_t > 0$ | $r_t \uparrow$ (above 1) | $r_t$ ended up below 1 |
| Bad Action | $\widehat{A}_t < 0$ | $r_t \downarrow$ (below 1) | $r_t$ ended up above 1 |

Even though gradient is computed from advantage this happens because:

1. **Conflicting samples fight over the same weights**: Two different state-action pairs might want the weights pulled in opposite directions. Because the network generalizes, the weight update that helps one can hurt the other.

2. **Multiple epochs on stale data**: PPO reuses the same batch for several gradient epochs (`num_learning_epochs`). So the advantages $\widehat{A}_t$ is frozen, but $\theta$ keeps moving across epochs. By epoch 4, the policy has shifted enough that a step taken to satisfy other samples can drag this sample's $r_t$ across to the wrong side of 1.

3. **Optimizer overshoot:** Momentum, learning rate, and the curvature of the loss surface mean a gradient step can overshoot.

**Code:**

```python
# Surrogate loss
ratio = torch.exp(actions_log_prob - torch.squeeze(batch.old_actions_log_prob)) 
surrogate = -torch.squeeze(batch.advantages) * ratio  
surrogate_clipped = -torch.squeeze(batch.advantages) * torch.clamp(
    ratio, 1.0 - self.clip_param, 1.0 + self.clip_param
)
surrogate_loss = torch.max(surrogate, surrogate_clipped).mean()
```

### 11.4 Value (Critic) Loss

**Value (Critic) Loss** trains $V_\phi$ toward the GAE returns $R_t$.

The critic $V_\phi(s)$ is the value-function network and its job is to predict the return from any state, and it feeds GAE. If critic is wrong: Advantage estimates are biased → Actor learns from bad signal → Everything downstream degrades.

So you have to train it by regressing it towards GAE returns $R_t = \widehat{A}_t + V(s_t)$.

$$V^{\text{clip}} = V_{\text{old}} + \mathrm{clip}(V - V_{\text{old}}, -\epsilon, +\epsilon),$$

Here the clip means that the $V$ can only drift by maximum $\epsilon$ before it is clipped.

So we take the larger of two square errors by making the loss more pessimistic.

$$L^V = \widehat{\mathbb{E}}_t\left[\max\left((V - R_t)^2,\ (V^{\text{clip}} - R_t)^2\right)\right].$$

> **NOTE:** Why bother clipping the value function at all → Because a critic that lurches around between epochs produces inconsistent baselines → Destabilizes advantage estimates that the actor depends on.
> Keep critic's updates measured → Whole actor-critic loop stable.

**Code:**

```python
value_clipped = batch.values + (values - batch.values).clamp(-self.clip_param, self.clip_param)
value_losses = (values - batch.returns).pow(2)
value_losses_clipped = (value_clipped - batch.returns).pow(2)
value_loss = torch.max(value_losses, value_losses_clipped).mean()
```

### 11.5 Entropy Bonus

**Entropy Bonus** measures how spread out the policy's action distribution is.

For Gaussian locomotion policy, entropy is a direct function of the action standard deviation:

- **High std**: Policy is exploring a wide range of actions
- **Low std**: Policy is deterministic and committed.

So Entropy bonus encourages exploration by rewarding higher policy entropy $H(\pi_\theta(\cdot \mid s))$.

**Code:** (comes from pytorch)

```python
entropy.mean()
```

### 11.6 Generalised Advantage Estimation (GAE)

Controls how good the advantage estimates are $\widehat{A}_t$ are.

Since policy gradient is basically just "*make actions with positive advantage more likely*", the quality of $\widehat{A}_t$ is what determines whether you are learning from signal or noise.

$$A(s_t, a_t) = Q(s_t, a_t) - V(s_t)$$

GAE estimates $\widehat{A}_t$.
> **NOTE**: $V(s)$ is the expected reward from a state regardless of which action is taken. It averages over all actions a policy would choose:
> $$V(s) = \mathbb{E}_{a \sim \pi}[Q(s, a)]$$

**One-step TD residual** is a one-step estimate of the advantage:

$$\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$

$$= \text{Reward you got} + \text{Value estimate of where you landed} - \text{Value where you started}$$

$$\widehat{A}_t^{(1)} = \delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$

$$\widehat{A}_t^{(2)} = \delta_t + \gamma\delta_{t+1} = r_t + \gamma r_{t+1} + \gamma^2 V(s_{t+1}) - V(s_t)$$

$$\widehat{A}_t^{(\infty)} = \sum_{l=0}^{\infty} \gamma^l r_{t+1} - V(s_t)$$

One-step estimate [$\widehat{A}_t^{(1)}$] has:

- **Low variance** as only one random reward and rest is value function, which is a smooth deterministic prediction
- **High bias** as it leans almost entirely on $V$ and $V$ is wrong especially early in training.

Monte-Carlo estimate [$\widehat{A}_t^{(\infty)}$] has:

- **High variance** as it accumulates the randomness of every reward, every action, every transition over the whole rest of the episode. In a locomotion rollout of hundreds of steps with stochastic dynamics, that's an enormous amount of noise piled into one number.
- Low bias because sum of actual rewards is an unbiased sample of the true return, no reliance on a flawed $V$ except baseline.

Therefore, GAE doesn't pluck on, but takes an exponentially weighted average of all of them at once:

$$\widehat{A}_t^{GAE(\gamma,\lambda)} = (1 - \lambda)\left(\widehat{A}_t^{(1)} + \lambda\widehat{A}_t^{(2)} + \lambda^2\widehat{A}_t^{(3)} + \ldots\right)$$

$$\widehat{A}_t^{GAE(\gamma,\lambda)} = \sum_{l=0}^{\infty} (\gamma\lambda)^l \delta_{t+1}$$

> $\lambda = 0$ → pure 1-step, fully trusts $V$  
> $\lambda = 1$ → Monte Carlo, ignores $V$ entirely  
> $\lambda = 0.95$ → mostly trusts $V$ but keeps a long tail of actual rewards as a correction  

> **NOTE**: $1-\lambda$ is just a normalisation factor to make the weights sum to 1.   
> Without it, weights are $1, \lambda, \lambda^2, \ldots$ which sum to $\frac{1}{1-\lambda}$ (geometric series). So the whole thing would be scaled up by that factor.  
> Multiplying by $(1-\lambda)$ cancels it:  
> $$(1-\lambda)(1 + \lambda + \lambda^2 + \ldots) = (1-\lambda) \cdot \frac{1}{1-\lambda} = 1$$

RSL-RL computes this using:

$$\widehat{A}_t = \delta_t + \gamma\lambda(1 - done_t)\widehat{A}_t$$

Where $done_t$ is just the flag that is set to 1 when the episode is completed.

$$R_t = \widehat{A}_t + V(s_t)$$

Where $R_t$ is the **return target** for the value function: the (bootstrapped, $\lambda$-weighted) estimate of the total discounted reward from step $t$ onward. It is the number the critic $V_\phi(s_t)$ is trained to predict.

**Complete code:**

<details>
<summary><strong>Click to expand Complete code: snippet</strong></summary>

```python
advantage = 0
for step in reversed(range(st.num_transitions_per_env)):
    # If we are at the last step, bootstrap the return value
    next_values = last_values if step == st.num_transitions_per_env - 1 else st.values[step + 1]

    # 1 if we are not in a terminal state, 0 otherwise
    next_is_not_terminal = 1.0 - st.dones[step].float()

    # TD error
    delta = st.rewards[step] + next_is_not_terminal * self.gamma * next_values - st.values[step]

    # Advantage
    advantage = delta + next_is_not_terminal * self.gamma * self.lam * advantage

    # Return
    st.returns[step] = advantage + st.values[step]
```

</details>

Here $\gamma$ is `gamma` and $\lambda$ is `lam` (see [Hyperparameters](#111-hyperparameters)).

### 11.7 Adaptive KL-based learning-rate schedule

In addition to clipping, RSL-RL's default for locomotion is an adaptive learning-rate schedule (`schedule`).

Each update it computes the mean KL between $\pi_{\theta_{\text{old}}}$ and $\pi_\theta$ over the minibatch (closed-form for the Gaussian policy, via `get_kl_divergence`) and adjusts the LR by a multiplicative factor:

1. if KL > $2 \times$ desired_kl: decrease LR (LR ← LR / 1.5)
2. if KL < desired_kl/2 (and > 0): increase LR (LR ← LR · 1.5)
3. LR is clamped to a range (e.g., [1e-5, 1e-2]).

**Code:**

```python
if kl_mean > self.desired_kl * 2.0:
    self.learning_rate = max(1e-5, self.learning_rate / 1.5)
elif kl_mean < self.desired_kl / 2.0 and kl_mean > 0.0:
    self.learning_rate = min(1e-2, self.learning_rate * 1.5)

for param_group in self.optimizer.param_groups:
    param_group["lr"] = self.learning_rate
```

The target `desired_kl` is listed in [Hyperparameters](#111-hyperparameters).

**Essentially**: *It acts as a soft trust region complementing the clip, keeping each update inside a stable policy-change budget regardless of reward scale.*

### 11.8 On-Policy data is used

*[Learn form current behaviour not from a buffer of old experience]*

PPO can only safely learn from data collected by the *current* policy. The moment the data is stale (collected by an older version of the policy), PPO's justification falls apart.

**Reason 1:** $r_t(\theta) = \frac{\pi_\theta(a_t \mid s_t)}{\pi_{\theta_{old}}(a_t \mid s_t)}$ would be pointless as $\pi_{\theta_{old}}$ is not actually the policy that led to a state $s_t$ from action $a_t$, if old data were to be used. So, the weights would be computed against the wrong reference, and the correction would be meaningless.

**Reason 2:** Advantages were estimated under the wrong state distribution.

Identity relating the returns of two policies:

$$J(\pi_{\text{new}}) = J(\pi_{\text{old}}) + \mathbb{E}_{s \sim \rho_{\pi_{\text{new}}},\ a \sim \pi_{\text{new}}}[A_{\pi_{\text{old}}}(s,a)]$$

$$\text{New policy's return} = \text{Old Policy's return} + \text{Advantages}_{\text{old policy}}\ \text{accumulated over states visited under the new policy}$$

But here, the expectation is over $\mathbf{\rho_{\pi_{\text{new}}}}$**, the new policy's state-visitation distribution**, which you do not have.

So PPO's surrogate makes an approximation by using $\rho_{\pi_{\text{new}}}$ with $\rho_{\pi_{\text{old}}}$. This gives:

$$L(\theta) = \mathbb{E}_{s \sim \rho_{\pi_{\text{old}}},\ a \sim \pi_{\text{old}}}[\ r_t(\theta)\ A_{\pi_{\text{old}}}(s,a)\ ].$$

But this is good, <u>only</u> when policies are close, which is what the clip enforces.

Advantage estimates $\widehat{A}_t$ were computed from rollouts drawn from the states the data-collecting policy actually visited, so they are <u>only meaningful for that state distribution</u>.

If data is stale, policy has moved on and now visits a different region of state space. So, states in your data no longer represent where the policy goes, and the approximation $\rho_{\pi_{\text{new}}} \approx \rho_{\pi_{\text{old}}}$ is badly wrong.

> **TLDR: PPO ONLY ON-POLICY**

### 11.9 Applying the gradients

After getting the loss:

```python
# Compute the gradients for PPO
self.optimizer.zero_grad()  # zero grad from prev iteration
loss.backward()  # backprop the loss to fill in .grad on every parameter

# Apply the gradients for PPO
nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
self.optimizer.step()
```

Note that `clip_param` clips the probability ratio inside the policy loss, but `max_grad_norm` clips the gradient magnitude during the optimiser step.

### 11.10 Privileged Learning

Inside PPO there are two networks:

- The **actor** $\pi_\theta(a \mid s)$: outputs actions. This is what will be deployed.
- The **critic** $V_\phi(s)$: outputs a single number, the estimated value of a state. It exists only to compute advantages $\widehat{A}_t$ (see [GAE](#116-generalised-advantage-estimation-gae)), which tell the actor's gradient which actions were better than expected.

The critic can consume anything available in simulation: terrain height-scan, exact base linear velocity, etc. As such it can predict $V(s)$ far more accurately → lower variance and better-targeted advantage estimates $\widehat{A}_t$. This makes the actor's gradient updates clearer and faster. But the critic is deleted once training is done, and is never deployed.

> **NOTE:** On the surface, "reuse the actor across tasks with fresh critics" and "distill into a shared student across teachers" look like they are after the same thing, but they are not.
>
> - The critic never tells the actor *what action to take*. It only tells the gradient *how good the action the actor already chose turned out to be, relative to expectation*. It shapes the learning signal; it does not supply target actions.
> - A teacher supplies exact target actions that the student copies via MSE.

The policy gradient is

$$\nabla_\theta J = \mathbb{E}[\nabla_\theta \log\pi_\theta(a \mid s)\ \widehat{A}_t].$$

The advantage uses a baseline, $\widehat{A}_t \approx Q(s,a) - V(s)$.

A foundational fact about policy gradients is that subtracting **any** baseline that is a function of **state only** (not action) reduces variance without introducing bias.

The reason is that the <u>expected score function</u> [$\mathbb{E}[\nabla_\theta \log\pi_\theta(a \mid s)\ \widehat{A}_t]$] $\times$ <u>a state-only term</u> [$b(s)$] $= 0$,

$$\mathbb{E}_{a \sim \pi_\theta}[\nabla_\theta \log\pi_\theta(a \mid s)\ b(s)] = b(s)\ \nabla_\theta \int \pi_\theta(a \mid s)\ da = b(s)\ \nabla_\theta 1 = 0,$$

so subtracting $b(s) = V(s)$ shifts nothing in expectation but cancels a great deal of noise.

> **NOTE**: **Variance** is about the **spread** of the gradient estimate across samples, and here the baseline does matter, because variance is not linear - it cares about the actual values, not just the average.

**Breakdown of the expectation equation**:

$$\mathbb{E}_a[\nabla_\theta \log\pi_\theta(a \mid s)] = \int \pi_\theta(a \mid s)\ \nabla_\theta \log\pi_\theta(a \mid s)\, da$$

Use the log-derivative trick in reverse: $\pi_\theta \nabla_\theta \log\pi_\theta = \nabla_\theta \pi_\theta$. So the integral becomes

$$\int \nabla_\theta \pi_\theta(a \mid s)\ da = \nabla_\theta \int \pi_\theta(a \mid s)\ da = \nabla_\theta(1) = 0$$

> ***Example**: if a score is* $100 \pm 2$*, it ranges over* $[98, 102]$*, so the bias is* $\pm 2$*. If you subtract 50 from the score, the range is still* $[48, 52]$*, so the bias (expected direction) is still* $\pm 2$*. Bias is unchanged, but smaller-magnitude gradients with the same expected direction means much less variance.*

**Privileged information** is part of the true simulator state $s$. So conditioning the baseline on it, $V(s_{\text{priv}})$, still keeps the gradient (asymptotically) unbiased while sharply cutting variance, because a more accurate baseline cancels more noise. Crucially, the privileged knowledge "leaks" into the actor <u>only through the scalar advantage number</u>, never through the <u>deployed input-output mapping</u>. The actor never sees a height-scan; it just receives better-shaped learning signals because of it.

> **NOTE:** When the actor is only **partially** observed (it sees proprioception like base angular velocity, joint positions, last action, etc., but **not** the privileged state), a small bias can creep into the policy gradient. The cause is the information **gap**: the critic's baseline $V(s)$ conditions on privileged variables (height-scan, true linear velocity, friction) that the actor never observed, so it is no longer a clean function of the actor's observation $o$ alone, and the baseline term stops cancelling exactly in expectation. So the equation becomes:
>
> $$\mathbb{E}_{a \sim \pi_\theta(\bullet \mid o)}[\nabla_\theta \log\pi_\theta(a \mid o)\ b(s)]$$
>
> where the state observed is no longer the same.

The clean fix is a value function defined over the actor's observation-history rather than over privileged state; in practice the variance reduction outweighs the small bias, so the privileged critic is used anyway.

---

## 12. Distillation using DAGGER (Student)

Section 11 trained the **teacher** with PPO, whose privileged critic could see information the real robot will never have. But the **deployed** policy can only use what the onboard sensors provide (proprioception + velocity commands). This section covers how that privileged knowledge is turned into a deployable **student**.

### 12.1 Teacher-Student Distillation Training

In a teacher-student distillation setup:

- The **teacher** (exteroceptive) is the PPO actor from Section 11, trained with RL using privileged terrain and state information.
- The **student** (proprioceptive-only) is trained to imitate the teacher. To compensate for the privileged observations it lacks (height-scan, base linear velocity), the student is given temporal memory - either a recurrent core (LSTM/GRU) or a stacked observation-history - so it can implicitly infer that missing state.
- In this repo, the **default** B2W student (`UnitreeB2WRoughDistillationRunnerCfg`) is a feed-forward MLP `[256, 128, 128]`; the recurrent LSTM student (`UnitreeB2WRoughDistillationRunnerRecurrentCfg`) is an **opt-in variant**, not the default.

This is better than training the proprioceptive policy directly with RL because of a clean division of labour:

- The privileged teacher solves the hard exploration and credit-assignment problem using information the student will never have.
- The student solves the easier problem of mimicking a known-good policy from limited sensing.

### 12.2 DAGGER (Dataset Aggregation)

#### 12.2.1 Behaviour Cloning

The naive alternative to DAgger is **Behaviour Cloning**:

- Collect a dataset of expert state-action pairs, then train the student by supervised learning to reproduce the expert's action at each state.
- **Flaw:** BC fits the student on states drawn from the expert's visitation distribution $\rho_{\pi^*}$. But at deployment, the student is the one driving the system, so it visits its own distribution $\rho_{\widehat{\pi}}$.
- This error compounds because:
  - Suppose the student matches the expert with small per-step error $\epsilon$.
  - The first time it errs, it lands in a state slightly off the expert's distribution, and so on.
  - Errors do not stay independent - they accumulate.
  - Result: BC's worst-case cost grows quadratically in the horizon $T$, because there are $T$ steps where a mistake can happen and a mistake at step $t$ can corrupt all of the roughly $T$ remaining steps.

$$\text{cost}_{BC} = O(T^2 \epsilon)$$

#### 12.2.2 DAgger

**DAgger** fixes this mismatch by training the student on its own state distribution. It iterates the following:

1. Roll out the current student to collect the states it actually visits.
2. Query the teacher for the correct action at each of those visited states.
3. Add these (student-visited state, teacher action) pairs to the dataset and retrain.

Since the student is now trained on exactly the states it will encounter when it drives the system, the train and deployment distributions match. This collapses the compounding and brings the cost down to linear in the horizon:

$$\text{cost}_{DAgger} = O(T\epsilon)$$

**What if there is no current student?** You just let the student run with its randomly initialised weights.

> **TLDR**: the student acts and is allowed to make mistakes, while the teacher only supplies labels.

#### 12.2.3 RSL-RL Implementation: DAgger

RSL-RL's Distillation algorithm is a streaming, single-iteration-per-rollout DAgger. The teacher and student are 2 separate model objects, `self.student` and `self.teacher` in `distillation.py`.

**Data collection (`act`):** the student picks the action that gets executed, and the teacher is asked, at that same state, what *it* would have done. That teacher action becomes the label.

<details>
<summary><strong>Click to expand PYTHON snippet</strong></summary>

```python
def act(self, obs: TensorDict) -> torch.Tensor:
    """Sample actions and store transition data."""
    # Compute the actions
    self.transition.actions = self.student(obs, stochastic_output=True).detach()
    self.transition.privileged_actions = self.teacher(obs).detach()

    # Record the observations
    self.transition.observations = obs

    return self.transition.actions
```

</details>

**Update (`update`):** the loss is a plain mean-squared error between the student's action and the teacher's label, accumulated over a window of steps before each optimisation step.

<details>
<summary><strong>Click to expand PYTHON snippet</strong></summary>

```python
def update(self) -> dict[str, float]:
    """Run optimization epochs over stored batches and return mean losses."""
    self.num_updates += 1
    mean_behavior_loss = 0  # used with counter to provide avg loss at the end
    loss = 0  # this builds up across several timesteps before each gradient step
    cnt = 0  # counts timesteps so we know when a window is full

    # Reuses same collected data for several epochs
    for epoch in range(self.num_learning_epochs):
        # restoring back hidden states from prev rollout
        self.student.reset(hidden_state=self.last_hidden_states[0])
        self.teacher.reset(hidden_state=self.last_hidden_states[1])
        self.student.detach_hidden_state()  # to ensure backprop don't flow into prev rollout

        # Inner loop walks the stored transitions Generator yields batches in sequential time
        # LSTM state
        for batch in self.storage.generator():
            # Forward pass + Loss:
            # Inference of the student for gradient computation
            actions = self.student(batch.observations)

            # Behavior cloning loss
            behavior_loss = self.loss_fn(actions, batch.privileged_actions)

            # Total loss Loss is accumulated first, rather than backprop immediately
            loss = loss + behavior_loss
            mean_behavior_loss += behavior_loss.item()  # report scalar value of the loss
            cnt += 1

            # Gradient step every gradient_length steps (default = 15) Actual optimisation step
            if cnt % self.gradient_length == 0:  # TBPTT
                self.optimizer.zero_grad()  # clears old gradient
                loss.backward()  # backprop through 15-step window
                if self.is_multi_gpu:  # averages gradients across GPUs so all ranks step identically.
                    self.reduce_parameters()
                if self.max_grad_norm:  # guard against occasional gradient spikes
                    nn.utils.clip_grad_norm_(self.student.parameters(), self.max_grad_norm)
                self.optimizer.step()  # updates students weights
                # cuts graph again to start fresh, but hold hidden state value
                self.student.detach_hidden_state()
                loss = 0

            # Reset dones "don't let one episode bleed into another"
            self.student.reset(batch.dones.view(-1))
            self.teacher.reset(batch.dones.view(-1))
            self.student.detach_hidden_state(batch.dones.view(-1))

    mean_behavior_loss /= cnt  # finalizes the average loss over all steps and epochs
    self.storage.clear()  # discard rollout
    self.last_hidden_states = (self.student.get_hidden_state(), self.teacher.get_hidden_state())
    self.student.detach_hidden_state()

    # Construct the loss dictionary
    loss_dict = {"behavior": mean_behavior_loss}

    return loss_dict
```

</details>

`loss_fn` is MSE by default (`loss_type="mse"`), so the whole objective is $L_{\text{BC}} = \lVert a_\theta^{\text{student}}(o^{\text{prop}}) - a^{\text{teacher}}(o^{\text{priv}}) \rVert_2^2.$ Truncated Backpropagation Through Time (TBPTT) is used.

> **NOTE:** The `update()` code is written generically for both MLP and LSTM students. When using the default MLP, all hidden-state calls (`reset`, `detach_hidden_state`) are no-ops and TBPTT just becomes "accumulate loss for `gradient_length` steps then backprop" - harmless for a feed-forward network. The recurrent machinery only activates when switching to the opt-in LSTM variant.

`gradient_length` is the main knob here:

- Too large → reintroduces the exploding gradients and memory blow-up of full BPTT.
- Too small → the student cannot learn dependencies longer than the window → starves the LSTM of the temporal context it needs to act as a state estimator.

> **TLDR**: here is the actual learning - loop epochs, MSE(student actions, teacher labels), `loss.backward()` every `gradient_length` steps, optional grad clip, `optimiser.step()`.

---

## 13. Code Walkthrough: train.py

### 13.1 PPO

<details>
<summary>Click to expand the PPO walkthrough</summary>

From `train.py`,

1. [Line 88](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L88): Note `DistillationRunner` is just there to act as guard for <u>point 4</u>

   ```python
   from rsl_rl.runners import DistillationRunner, OnPolicyRunner
   ```

2. [Line 205-206](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L205-L206):

   ```python
   runner = OnPolicynRunner(env, agent_cfg.to_dict(), log_dir=log_dir, device=agent_cfg.device)
   ```

   - [Line 39-40](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L39-L40) of `on_policy_runner.py`:

     ```python
     # Create the algorithm
     alg_class: type[PPO] = resolve_callable(self.cfg["algorithm"]["class_name"])
     self.alg = alg_class.construct_algorithm(obs, self.env, self.cfg, self.device)
     ```

     1. Since `cfg["algorithm"]["class_name"] == "PPO"`, it then calls `PPO.construct_algorithm()` in `ppo.py`.
     2. [Line 476-478](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/ppo.py#L476-L478), builds actor-critic class:

        ```python
        alg_class: type[PPO] = resolve_callable(cfg["algorithm"].pop("class_name")
        actor_class: type[MLPModel] = resolve_callable(cfg["actor"].pop("class_name"))
        critic_class: type[MLPModel] = resolve_callable(cfg["critic"].pop("class_name"))
        ```

     3. [Lines 493-501](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/ppo.py#L493-L501) initialise the Actor, Critic, followed by RolloutStorage, and the PPO object which is the `self.alg`

3. If resume, previously trained model is loaded in, through [Line 214-217](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L214-L217):

   ```python
   if agent_cfg.resume or agent_cfg.algorithm.class_name == "Distillation":
       print(f"[INFO]: Loading model checkpoint from: {resume_path}")
       # load previously trained model
       runner.load(resume_path)
   ```

4. [Line 224](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L224):

   ```python
   runner.learn(num_learning_iterations=agent_cfg.max_iterations, init_at_random_ep_len=True)
   ```

   a. [Line 66](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L66) in `on_policy_runner` calls `train_mode()`, which is called on `ppo.py` as well:

      1. On `ppo.py`, both actor and critic are set to train, in [Line 418-421](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/ppo.py#L418-L421):

         ```python
         def train_mode(self) -> None:
             """Set train mode for learnable models."""
             self.actor.train()
             self.critic.train()
         ```

         Note that the `train()` method here is from MLP library

   b. [Line 76 – 105](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L76-L105) is the entire training process.

      ```python
      # Start training
      start_it = self.current_learning_iteration
      total_it = start_it + num_learning_iterations
      for it in range(start_it, total_it):
          start = time.time()
          # Rollout
          with torch.inference_mode():
              for _ in range(self.cfg["num_steps_per_env"]):
                  # Sample actions
                  actions = self.alg.act(obs)
                  # Step the environment
                  obs, rewards, dones, extras = self.env.step(actions.to(self.env.device))
                  # Check for NaN values from the environment
                  if self.cfg.get("check_for_nan", True):
                      check_nan(obs, rewards, dones)
                  # Move to device
                  obs, rewards, dones = (obs.to(self.device), rewards.to(self.device), dones.to(self.device))
                  # Process the step
                  self.alg.process_env_step(obs, rewards, dones, extras)
                  # Extract intrinsic rewards if RND is used (only for logging)
                  intrinsic_rewards = self.alg.intrinsic_rewards if self.cfg["algorithm"]["rnd_cfg"] else None
                  # Book keeping
                  self.logger.process_env_step(rewards, dones, extras, intrinsic_rewards)

          stop = time.time()
          collect_time = stop - start
          start = stop
          # Compute returns
          self.alg.compute_returns(obs)
      ```

   c. Subsequently in [line 108](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L108), the `update()` function from earlier is called, which does the main loss calculation and backprop.

      ```python
      # Update policy
      loss_dict = self.alg.update()
      ```

</details>

### 13.2 Distillation (MLP Student)

<details>
<summary>Click to expand the MLP student walkthrough</summary>

From `train.py`,

1. [Line 88](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L88): Note `DistillationRunner` is just there to act as guard for <u>point 4</u>

   ```python
   from rsl_rl.runners import DistillationRunner, OnPolicyRunner
   ```

2. [Line 207-208](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L207-L208):

   ```python
   runner = DistillationRunner(env, agent_cfg.to_dict(), log_dir=log_dir, device=agent_cfg.device)
   ```

   a. From here `DistillationRunner` has no `__init__`, so `OnPolicyRunner.__init__`

   b. [Line 39-40](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L39-L40) of `on_policy_runner.py`:

      ```python
      alg_class: type[PPO] = resolve_callable(self.cfg["algorithm"]["class_name"])
      self.alg = alg_class.construct_algorithm(obs, self.env, self.cfg, self.device)
      ```

      1. Since `cfg["algorithm"]["class_name"] == "Distillation"`, it then calls `Distilation.construct_algorithm()` in `distillation.py`. In `construct_algorithm()`, new student of type MLP model is randomly initialised, as defined in `distillation.py`.
      2. [Line 238-240](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/distillation.py#L238-L240):

         ```python
         alg_class: type[Distillation] = resolve_callable(cfg["algorithm"].pop("class_name"))
         student_class: type[MLPModel] = resolve_callable(cfg["student"].pop("class_name"))
         teacher_class: type[MLPModel] = resolve_callable(cfg["teacher"].pop("class_name"))
         ```

      3. [Lines 254-270](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/distillation.py#L254-L270) initialise the Student, Teacher, followed by RolloutStorage, and the Distillation object which is the `self.alg`

3. [Line 217](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L217):

   ```python
   runner.load(resume_path)
   ```

   a. This calls `OnPolicyRunner.load()` in [Line 145](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L145), which calls Distillation algorithm's `load()` function, in [Line 158](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L158):

      ```python
      load_iteration = self.alg.load(loaded_dict, load_cfg, strict)
      ```

      1. The objective of this line is to load the teacher
      2. NOTE: By default, when student is trained from scratch, `load_cfg = None`, and `distillation.py` will leave the random student initialised earlier, untouched.
      3. BUT, if training from existing, student, `load_cfg` must be set before `runner.load()`

         So, `load_cfg` just loads student in as warm_start, setting "student" as True.

4. [Line 224](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L224):

   ```python
   runner.learn(num_learning_iterations=agent_cfg.max_iterations, init_at_random_ep_len=True)
   ```

   a. Overriden by `distillation_runner.py`, the one method it overrides. Which just acts as a guard to check whether teacher is loaded.

   b. [Line 66](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L66) in `on_policy_runner` calls `train_mode()`, which is called on `distillation.py` as well:

      ```python
      self.alg.train_mode()
      ```

      1. On `distillation.py`, student is set to train, and teacher is set to eval, [Line 169-174](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/distillation.py#L169-L174):

         ```python
         def train_mode(self) -> None:
             """Set train mode for the student and keep the teacher in eval mode."""
             self.student.train()
             # Teacher is always in eval mode
             self.teacher.eval()
         ```

   c. [Line 76 – 105](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L76-L105) is the entire training process.

      ```python
      # Start training
      start_it = self.current_learning_iteration
      total_it = start_it + num_learning_iterations
      for it in range(start_it, total_it):
          start = time.time()
          # Rollout
          with torch.inference_mode():
              for _ in range(self.cfg["num_steps_per_env"]):
                  # Sample actions
                  actions = self.alg.act(obs)
                  # Step the environment
                  obs, rewards, dones, extras = self.env.step(actions.to(self.env.device))
                  # Check for NaN values from the environment
                  if self.cfg.get("check_for_nan", True):
                      check_nan(obs, rewards, dones)
                  # Move to device
                  obs, rewards, dones = (obs.to(self.device), rewards.to(self.device), dones.to(self.device))
                  # Process the step
                  self.alg.process_env_step(obs, rewards, dones, extras)
                  # Extract intrinsic rewards if RND is used (only for logging)
                  intrinsic_rewards = self.alg.intrinsic_rewards if self.cfg["algorithm"]["rnd_cfg"] else None
                  # Book keeping
                  self.logger.process_env_step(rewards, dones, extras, intrinsic_rewards)

          stop = time.time()
          collect_time = stop - start
          start = stop
          # Compute returns
          self.alg.compute_returns(obs)
      ```

   d. Subsequently in [line 108](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L108), the `update()` function from earlier is called, which does the main loss calculation and backprop.

      ```python
      # Update policy
      loss_dict = self.alg.update()
      ```

</details>

### 13.3 Distillation (LSTM Student)

<details>
<summary>Click to expand the LSTM student walkthrough</summary>

From `train.py`,

1. [Line 88](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L88): Note `DistillationRunner` is just there to act as guard for <u>point 4</u>

   ```python
   from rsl_rl.runners import DistillationRunner, OnPolicyRunner
   ```

2. [Line 207-208](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L207-L208):

   ```python
   runner = DistillationRunner(env, agent_cfg.to_dict(), log_dir=log_dir, device=agent_cfg.device)
   ```

   a. From here `DistillationRunner` has no `__init__`, so `OnPolicyRunner.__init__`

   b. [Line 39-40](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L39-L40) of `on_policy_runner.py`:

      ```python
      alg_class: type[PPO] = resolve_callable(self.cfg["algorithm"]["class_name"])
      self.alg = alg_class.construct_algorithm(obs, self.env, self.cfg, self.device)
      ```

      1. Since `cfg["algorithm"]["class_name"] == "Distillation"`, it then calls `Distilation.construct_algorithm()` in `distillation.py`. The only thing that changes from the MLP case is the **student** config: the recurrent variant sets `student = RslRlRNNModelCfg(..., rnn_type="lstm")`, whose `class_name == "RNNModel"`. So in `construct_algorithm()`, a new student of type **RNNModel** (an LSTM wrapper that holds a hidden state `h`/`c`) is randomly initialised. The **teacher stays an MLP**, since it is the frozen Phase-1 actor.
      2. [Line 238-240](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/distillation.py#L238-L240):

         ```python
         alg_class: type[Distillation] = resolve_callable(cfg["algorithm"].pop("class_name"))
         student_class: type[RNNModel] = resolve_callable(cfg["student"].pop("class_name"))  # "RNNModel"
         teacher_class: type[MLPModel] = resolve_callable(cfg["teacher"].pop("class_name"))
         ```

      3. [Lines 254-270](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/distillation.py#L254-L270) initialise the Student, Teacher, followed by RolloutStorage, and the Distillation object which is the `self.alg`

3. [Line 217](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L217):

   ```python
   runner.load(resume_path)
   ```

   a. This calls `OnPolicyRunner.load()` in [Line 145](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L145), which calls Distillation algorithm's `load()` function, in [Line 158](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L158):

      ```python
      load_iteration = self.alg.load(loaded_dict, load_cfg, strict)
      ```

      1. The objective of this line is to load the teacher
      2. NOTE: By default, when student is trained from scratch, `load_cfg = None`, and `distillation.py` will leave the random student initialised earlier, untouched.
      3. BUT, if training from existing, student, `load_cfg` must be set before `runner.load()`

         So, `load_cfg` just loads student in as warm_start, setting "student" as True.

4. [Line 224](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L224):

   ```python
   runner.learn(num_learning_iterations=agent_cfg.max_iterations, init_at_random_ep_len=True)
   ```

   a. Overriden by `distillation_runner.py`, the one method it overrides. Which just acts as a guard to check whether teacher is loaded.

   b. [Line 66](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L66) in `on_policy_runner` calls `train_mode()`, which is called on `distillation.py` as well:

      ```python
      self.alg.train_mode()
      ```

      1. On `distillation.py`, student is set to train, and teacher is set to eval, [Line 169-174](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/algorithms/distillation.py#L169-L174):

         ```python
         def train_mode(self) -> None:
             """Set train mode for the student and keep the teacher in eval mode."""
             self.student.train()
             # Teacher is always in eval mode
             self.teacher.eval()
         ```

   c. [Line 76 – 105](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L76-L105) is the entire training process.

      ```python
      # Start training
      start_it = self.current_learning_iteration
      total_it = start_it + num_learning_iterations
      for it in range(start_it, total_it):
          start = time.time()
          # Rollout
          with torch.inference_mode():
              for _ in range(self.cfg["num_steps_per_env"]):
                  # Sample actions
                  actions = self.alg.act(obs)
                  # Step the environment
                  obs, rewards, dones, extras = self.env.step(actions.to(self.env.device))
                  # Check for NaN values from the environment
                  if self.cfg.get("check_for_nan", True):
                      check_nan(obs, rewards, dones)
                  # Move to device
                  obs, rewards, dones = (obs.to(self.device), rewards.to(self.device), dones.to(self.device))
                  # Process the step
                  self.alg.process_env_step(obs, rewards, dones, extras)
                  # Extract intrinsic rewards if RND is used (only for logging)
                  intrinsic_rewards = self.alg.intrinsic_rewards if self.cfg["algorithm"]["rnd_cfg"] else None
                  # Book keeping
                  self.logger.process_env_step(rewards, dones, extras, intrinsic_rewards)

          stop = time.time()
          collect_time = stop - start
          start = stop
          # Compute returns
          self.alg.compute_returns(obs)
      ```

   d. Subsequently in [line 108](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L108), the `update()` function from earlier is called, which does the main loss calculation and backprop.

      ```python
      # Update policy
      loss_dict = self.alg.update()
      ```

> **What actually differs from the MLP run:** `act()`, the rollout loop, and `update()` are the *same generic code*. With the LSTM student the hidden-state machinery inside them (`student.reset(...)`, `detach_hidden_state(...)`, and the `gradient_length`-windowed TBPTT) stops being a no-op and starts carrying/cutting the `h`/`c` state across timesteps. The recurrent config also retunes the algorithm for this: `gradient_length = 24` (widen the TBPTT window to the full rollout so the student integrates a gait cycle of history for velocity inference) and `max_grad_norm = 1.0` (clip BPTT gradients that would otherwise explode through the unrolled LSTM). See [Teacher-Student Distillation Training](#121-teacher-student-distillation-training) and the [RSL-RL DAgger `update()`](#1223-rsl-rl-implementation-dagger) walkthrough for the hidden-state calls.

</details>

### 13.4 Multi-Expert Distillation (LSTM Student)

<details>
<summary>Click to expand the multi-expert LSTM student walkthrough</summary>

This is the run from [Section 5.6](#56-multi-expert-terrain): one LSTM student distilled from **N frozen MLP experts** at once, each env supervised by the expert matching its terrain. The student is identical to [Section 13.3](#133-distillation-lstm-student); only the **algorithm** changes - `MultiTeacherDistillation` (a subclass of RSL-RL `Distillation`) holds N teachers instead of one and routes supervision per env. From `train.py`,

1. [Line 88](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L88): Note `DistillationRunner` is just there to act as guard for <u>point 4</u>

   ```python
   from rsl_rl.runners import DistillationRunner, OnPolicyRunner
   ```

2. [Line 207-208](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L207-L208):

   ```python
   runner = DistillationRunner(env, agent_cfg.to_dict(), log_dir=log_dir, device=agent_cfg.device)
   ```

   a. From here `DistillationRunner` has no `__init__`, so `OnPolicyRunner.__init__`

   b. [Line 39-40](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L39-L40) of `on_policy_runner.py`:

      ```python
      alg_class: type[PPO] = resolve_callable(self.cfg["algorithm"]["class_name"])
      self.alg = alg_class.construct_algorithm(obs, self.env, self.cfg, self.device)
      ```

      1. The difference starts here. `cfg["algorithm"]["class_name"]` is **not** the plain `"Distillation"` - it is the dotted path `robot_lab...multiteacher.MultiTeacherDistillation` (set by `rsl_rl_multiexpert_distillation_cfg.py`). So `resolve_callable` imports our subclass and calls [`MultiTeacherDistillation.construct_algorithm()`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py#L77-L117) instead of the stock one.
      2. As in [Section 13.3](#133-distillation-lstm-student), the **student** is an `RNNModel` (LSTM, holds hidden state `h`/`c`) and the **teacher** class is the MLP actor. But the teachers are loaded *here*, from the env cfg, not from a single `--load_run` checkpoint - [`multiteacher.py` line 86-103](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py#L86-L103):

         ```python
         env_cfg = env.unwrapped.cfg
         ckpts: list[str] = env_cfg.teacher_checkpoints      # one per teachers.txt line
         column_to_expert: list[int] = env_cfg.column_to_expert

         student = student_class(obs, cfg["obs_groups"], "student", env.num_actions, **cfg["student"]).to(device)
         teachers = []
         for path in ckpts:
             teacher_kwargs = copy.deepcopy(cfg["teacher"])   # ctor pops nested keys; deep-copy per teacher
             t = teacher_class(obs, cfg["obs_groups"], "teacher", env.num_actions, **teacher_kwargs).to(device)
             sd = torch.load(path, map_location=device, weights_only=False)
             t.load_state_dict(sd.get("teacher_state_dict") or sd["actor_state_dict"], strict=True)
             t.eval()
             teachers.append(t)
         ```

      3. The constructor then maps **each env to its expert** from the static terrain column assignment - [`multiteacher.py` line 24-36](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py#L24-L36). `super().__init__(student, teachers[0], ...)` reuses the base `Distillation` setup (student optimizer, storage, loss); `teachers[0]` is just a stand-in for `self.teacher`. The real list is `self.teachers`, and `self.expert_ids` is a `[num_envs]` tensor giving the expert id for every robot:

         ```python
         super().__init__(student, teachers[0], storage, **kwargs)
         self.teachers = nn.ModuleList(teachers).to(self.device)
         terrain = env.unwrapped.scene.terrain
         col2exp = torch.as_tensor(column_to_expert, dtype=torch.long, device=self.device)
         self.expert_ids = col2exp[terrain.terrain_types.to(self.device)]  # [num_envs]
         self.teacher_loaded = True
         ```

3. [Line 214-217](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L214-L217):

   ```python
   if agent_cfg.resume or agent_cfg.algorithm.class_name == "Distillation":
       print(f"[INFO]: Loading model checkpoint from: {resume_path}")
       runner.load(resume_path)
   ```

   a. **This branch is skipped.** `agent_cfg.algorithm.class_name` is the dotted `MultiTeacherDistillation` path, not the literal `"Distillation"`, and `resume` is False on a fresh run. So `runner.load()` is **not** called and `--load_run` is not required - the teachers were already loaded inside `construct_algorithm()` in <u>point 2b</u>. (Contrast [Section 13.3](#133-distillation-lstm-student) point 3, where the single teacher is loaded via `runner.load()`.)

4. [Line 224](../robot_lab/scripts/reinforcement_learning/rsl_rl/train.py#L224):

   ```python
   runner.learn(num_learning_iterations=agent_cfg.max_iterations, init_at_random_ep_len=True)
   ```

   a. Overriden by `distillation_runner.py`, the one method it overrides. Which just acts as a guard to check whether teacher is loaded (here `self.teacher_loaded = True` is set in the constructor, so the guard passes).

   b. [Line 66](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L66) in `on_policy_runner` calls `train_mode()`, overridden in [`multiteacher.py` line 56-59](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py#L56-L59) to put the student in train and **every** teacher in eval:

      ```python
      def train_mode(self) -> None:
          self.student.train()
          for t in self.teachers:
              t.eval()
      ```

   c. [Line 76 - 105](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L76-L105) is the entire training process - the *same generic loop* as PPO/Distillation. The only methods that change are the two it calls, both overridden in `multiteacher.py`:

      1. `act()` ([line 38-44](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py#L38-L44)) - the student acts as usual, but the supervision target is **gathered per env** from the matching expert. All N teachers run on the full obs, then `expert_ids` selects each env's column:

         ```python
         def act(self, obs: TensorDict) -> torch.Tensor:
             self.transition.actions = self.student(obs, stochastic_output=True).detach()
             targets = torch.stack([t(obs) for t in self.teachers], dim=0)        # [E, N, A]
             idx = self.expert_ids.view(1, -1, 1).expand(1, -1, targets.shape[-1]) # [1, N, A]
             self.transition.privileged_actions = targets.gather(0, idx).squeeze(0).detach()
             self.transition.observations = obs
             return self.transition.actions
         ```

      2. `process_env_step()` ([line 46-54](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py#L46-L54)) - stores the transition and resets hidden state on `dones` for the student **and every teacher** (same LSTM hidden-state machinery as [Section 13.3](#133-distillation-lstm-student), now looped over all experts):

         ```python
         self.student.reset(dones)
         for t in self.teachers:
             t.reset(dones)
         ```

   d. Subsequently in [line 108](../../../isaac-sim/kit/python/lib/python3.11/site-packages/rsl_rl/runners/on_policy_runner.py#L108), the inherited `update()` runs the MSE loss between student actions and the per-env `privileged_actions`, then backprops - identical to [Section 13.3](#133-distillation-lstm-student), including the `gradient_length = 24` TBPTT window and `max_grad_norm = 1.0` clipping.

      ```python
      # Update policy
      loss_dict = self.alg.update()
      ```

5. On save, `save()` ([line 66-75](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/distillation/multiteacher.py#L66-L75)) writes the `student_state_dict` plus a per-expert `teacher_<i>_state_dict`, and keeps a plain `teacher_state_dict` (= teacher 0) so the stock single-teacher loader and `play.py` stay happy:

   ```python
   saved = {
       "student_state_dict": self.student.state_dict(),
       "optimizer_state_dict": self.optimizer.state_dict(),
       "teacher_state_dict": self.teachers[0].state_dict(),
   }
   for i, t in enumerate(self.teachers):
       saved[f"teacher_{i}_state_dict"] = t.state_dict()
   ```

> **What actually differs from the single-teacher LSTM run ([Section 13.3](#133-distillation-lstm-student)):** the runner, rollout loop, and `update()` are unchanged. Only the algorithm swaps to `MultiTeacherDistillation`, which (i) loads N MLP teachers from `teachers.txt` inside `construct_algorithm()` instead of one via `runner.load()` - so the `train.py` load branch is skipped and `--load_run` is not needed, (ii) builds a `[num_envs]` `expert_ids` map from the terrain columns, and (iii) in `act()`/`process_env_step()`/`save()` routes the supervision target per env and resets/saves every teacher. The student and its LSTM hidden-state handling are exactly as in Section 13.3. See [Section 5.6](#56-multi-expert-terrain) for how `teachers.txt` builds the combined terrain and `column_to_expert` map.

</details>

---
