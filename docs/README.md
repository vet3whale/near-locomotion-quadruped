# Training to Deployment Pipeline for Unitree B2W (near-locomotion-quadruped repo)

> **Branch:** this documentation lives on the `b2w-rough-walking` branch of the main repo.

The B2W has 16 DOF: 12 leg joints (FR/FL/RR/RL × hip/thigh/calf) controlled by position PD, and 4 wheel joints (FR/FL/RR/RL foot). Three submodule repos work together:

| Repo | Role |
|---|---|
| `robot_lab/` | Isaac Lab task definitions, training config, and `train.py` / `play.py` scripts - where the RL policy is trained and exported to ONNX |
| `unitree_rl_lab/` | C++ deployment controller (`deploy/robots/b2w/`) that loads the ONNX policy and sends joint commands over DDS |
| `unitree_mujoco/` | MuJoCo simulator that receives DDS commands and simulates the B2W - used for sim2sim validation before deploying to the real robot |

The RL policy is trained in `robot_lab`, exported to ONNX via `play.py`, then the C++ controller in `unitree_rl_lab` loads that ONNX and runs it against either `unitree_mujoco` (sim2sim) or the real robot (sim2real) over DDS.

> **Note**: `source/robot_lab/tasks/.../unitree_b2w/` refers to `robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/`

## Table of Contents

- [Repository Layout](#repository-layout)
- [Environment Setup](#environment-setup)
  - [System Container Was Tested On](#system-container-was-tested-on)
  - [What the Container Downloads](#what-the-container-downloads)
  - [Quick Start - Dev Container](#quick-start---dev-container)
  - [Shell Functions](#shell-functions)
  - [Reference - `--load_actor_only` flag](#reference---load_actor_only-flag)
- [MuJoCo Sim2Sim Validation Setup](#mujoco-sim2sim-validation-setup)
  - [Overview](#overview)
  - [Code Changes Made](#code-changes-made)
  - [Prerequisite Installation](#prerequisite-installation)
  - [Check this before running sim2sim](#check-this-before-running-sim2sim)
  - [Terrain Generation](#terrain-generation)
  - [Switching to Gamepad](#switching-to-gamepad)
- [Workflow](#workflow)
  - [Step 1 - Train in Isaac Lab](#step-1---train-in-isaac-lab)
  - [Step 1b - Watch the Robot Walk in Isaac Sim](#step-1b---watch-the-robot-walk-in-isaac-sim)
  - [Step 2 - Export to ONNX](#step-2---export-to-onnx)
  - [Step 3 - Sim2Sim in MuJoCo](#step-3---sim2sim-in-mujoco)
  - [Step 3b - Generate rough terrain](#step-3b---generate-rough-terrain)
- [Rough Terrain Curriculum Training on Isaac-Sim](#rough-terrain-curriculum-training-on-isaac-sim)
  - [Training Command](#training-command)
  - [Sub-Terrains](#sub-terrains)
  - [Terrain Difficulty Curriculum](#terrain-difficulty-curriculum)
  - [Implementing different terrain config (To be implemented)](#implementing-different-terrain-config-to-be-implemented)
- [Skills Trained On](#skills-trained-on)
  - [Successfully trained on](#successfully-trained-on)
  - [What we want to train on next](#what-we-want-to-train-on-next)
- [Deriving π in RL](#deriving-π-in-rl)
  - [Defining Q-function](#defining-q-function)
- [Proximal Policy Optimisation: PPO](#proximal-policy-optimisation-ppo)
  - [The Combined PPO Loss](#the-combined-ppo-loss)
  - [Clipped Surrogate Objective](#clipped-surrogate-objective)
  - [Value (Critic) Loss](#value-critic-loss)
  - [Entropy Bonus](#entropy-bonus)
  - [Generalised Advantage Estimation (GAE)](#generalised-advantage-estimation-gae)
  - [Adaptive KL-based learning-rate schedule](#adaptive-kl-based-learning-rate-schedule)
  - [On-Policy data is used](#on-policy-data-is-used)
  - [Applying the gradients](#applying-the-gradients)
- [Code Walkthrough: train.py](#code-walkthrough-trainpy)
  - [PPO](#ppo)

---
## Repository Layout

**Key Folders:**
```
near-locomotion-quadruped/
├── robot_lab/                                         ← train & export (Isaac Lab)
│   └── source/robot_lab/tasks/.../unitree_b2w/       ← task definition, env cfg, PPO cfg
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
---

## Environment Setup

### System Container Was Tested On

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

> **Key idea:** there are *two* Python worlds in this container. Isaac Sim's **Python 3.11** is used for all Isaac Lab training and playing; the system **Python 3.12** is used for ROS 2 and standalone tooling. The two are kept isolated so they don't contaminate each other.

> **Driver note:** NVIDIA driver **595 does not work** with Isaac Sim 5.1 - it causes the app to crash on startup ([issue #568](https://github.com/isaac-sim/IsaacSim/issues/568)). Isaac Sim 5.1 was only tested on the **580** driver branch at release time and driver 595 introduced changes that broke compatibility. Use driver **580.x** (the version in the table above is confirmed working).

### What the Container Downloads

The Dockerfile pulls the following during `docker build`. Plan for a large first build (~30–40 GB total download).

| What | Source | Size (approx) |
|---|---|---|
| `nvcr.io/nvidia/isaac-sim:5.1.0` base image | NGC (`nvcr.io`) | ~25 GB |
| ROS 2 Humble packages (`ros-humble-ros-base`, `rmw-cyclonedds-cpp`, colcon, compat libs) | `packages.ros.org` | ~300 MB |
| Isaac Sim Python 3.11 deps (`rsl-rl-lib`, `flatdict`, `h5py`, `onnx`, `GitPython`, etc.) | PyPI (`--no-deps`) | ~100 MB |
| `cusrl` | PyPI | ~10 MB |
| Standalone PyTorch venv (`torch`, `torchvision`, `torchaudio` CUDA 12.8 nightly) | `download.pytorch.org` | ~4 GB |

> The standalone PyTorch venv (last row) is for non-Isaac tooling only. Comment it out in the Dockerfile to speed up builds if you don't need it.

### Quick Start - Dev Container

The repo ships a `.devcontainer/` at its root. Prerequisites:

- NVIDIA GPU host with `nvidia-container-toolkit` installed
- Docker
- VS Code with the **Dev Containers** extension

1. **Clone the repo with its submodules** (`robot_lab`, `unitree_mujoco`, `unitree_rl_lab`):

   ```bash
   git clone <repo-url> near-locomotion-quadruped
   cd near-locomotion-quadruped
   ```

2. **Initialise the submodules** (skip if you already used `--recurse-submodules` on the clone):

   ```bash
   git submodule init
   ```

3. **Fetch the submodule contents:**

   ```bash
   git submodule update --recursive
   ```

   > Steps 2–3 can be combined as `git submodule update --init --recursive`.

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

6. **Verify Isaac Sim works.** Run the drop-sphere sanity check. It will open Isaac Sim GUI and drops a physics sphere onto a ground plane. If it renders and the sphere falls, Isaac Sim is working correctly.

   ```bash
   cd /workspace/near-locomotion-quadruped
   /isaac-sim/python.sh drop_sphere.py
   ```

   Close the window when done. If it crashes on startup, check the NVIDIA driver version (see [System Container Was Tested On](#system-container-was-tested-on) — driver 595 is known broken).

### Shell Functions

The dev container's `~/.bashrc` defines two functions. Call each once per terminal as needed:

| Function | When to call | What it does |
|---|---|---|
| `setup_isaaclab` | Before any Isaac Lab script (`train.py`, `play.py`) | Unsets `PYTHONPATH`, sources Isaac Sim's Python env, adds Isaac Lab + robot_lab packages to `PYTHONPATH`, and aliases `python`/`python3` to Python 3.11 |
| `sim2sim_env` | Before running `unitree_mujoco` or `b2w_ctrl` | Unsets ROS env vars that would interfere with DDS, sets `LD_LIBRARY_PATH` for the controller's shared libs, and sets the `CYCLONEDDS_URI` to disable Iceoryx (loopback sim2sim) |

### Reference - `--load_actor_only` flag

To load a flat-terrain checkpoint into the rough-terrain task, you **must** pass `--load_actor_only`:

```bash
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

The rough critic receives privileged observations (height scans, contact forces, terrain geometry) that the flat critic never saw. The flat checkpoint's critic weights are shaped `[hidden, 60]`, which doesn't fit the rough critic's expected `[hidden, 247]`, so loading fails. Since `play` only runs the actor forward, `--load_actor_only` skips the critic on load entirely.

This flag is not needed when loading a rough-trained checkpoint into the rough task - the critic architectures match and the normal load path works.

---

## MuJoCo Sim2Sim Validation Setup

This section explains how to set up Sim2Sim validation using MuJoCo - running the trained ONNX policy against the MuJoCo simulator over DDS on loopback, without a physical robot. It covers the one-time build steps, the code changes made to each submodule, and how to run the full sim2sim loop.

### Overview

**Training policy location** (auto-selected by `parser_policy_dir`):
```
robot_lab/logs/rsl_rl/unitree_b2w_rough/<latest-timestamp>/
  exported/policy.onnx ← not committed to github; run play.py first to export it
```

To set which policy the controller deploys (for sim2sim or sim2real), open `unitree_rl_lab/deploy/robots/b2w/config/config.yaml` and edit `policy_dir` to point at the log root of the run you want. The `parser_policy_dir` function in the controller then automatically finds the most recent timestamp subdirectory that contains an `exported/` folder and loads `policy.onnx` from it - so you never need to copy files manually. See [Step 2 - Export to ONNX](#step-2---export-to-onnx) for how to generate the ONNX file from a checkpoint using `play.py`.

**Shared deploy config** (loaded by the controller at startup):
```
unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml  ← observation/action config (editable)
```

### Code Changes Made

#### Shared headers (unitree_rl_lab)

These files are shared across all robots. Changes are backward-compatible and gated so
existing robots (b2, go2, h1, g1_29dof) are unaffected.

##### 1. `deploy/include/FSM/FSMState.h` - keyboard FSM transitions

| Action | Why |
|---|---|
| Added a `keyboard_transitions` parsing block immediately after the existing `transitions` block and before `// register for all states` (code below). | When `FSMState::keyboard` is `nullptr` (robots that don't initialize it in `main.cpp`), the block is skipped - so existing robots (b2, go2, h1, g1_29dof) are unaffected. Transitions are edge-triggered (`on_pressed`, not held), so a brief keypress advances the FSM. |

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

The `keyboard_transitions` YAML block in `config.yaml` maps target-state name → key string:

```yaml
keyboard_transitions:
  FixStand: "f"
  Passive:  "x"
```

##### 2. `deploy/include/isaaclab/envs/mdp/observations/observations.h` - wheel-masked joint positions

| Action | Why |
|---|---|
| Added a generic observation `joint_pos_rel_without_wheel` between `joint_pos_rel` and `joint_vel_rel` (code below); wheel indices are read from `deploy.yaml`. | The B2W policy was trained with `joint_pos_rel_without_wheel`: a 16-element `q - q_default` vector where the four wheel slots [12–15] are forced to 0.0 - wheel position is undefined for continuously-spinning joints, so feeding the raw value there is wrong. Output length always equals the full joint count (16) to match the policy input dimension. |

```cpp
// Like joint_pos_rel, but zeroes the slots listed in params["wheel_joint_ids"].
// Output length always equals the full joint count (16 for B2W), matching the
// policy input dimension. Wheel slots are trained on 0.0 (position undefined
// for continuously-spinning wheels), so feeding q-q_default there is wrong.
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

The wheel indices are read from `deploy.yaml`:

```yaml
joint_pos_rel_without_wheel:
  params: {wheel_joint_ids: [12, 13, 14, 15]}
```

##### 3. `deploy/include/FSM/State_SitDown.h` - two-phase sit-down state

| Action | Why |
|---|---|
| New FSM state with two phases, then auto-transitions to Passive. **Phase 1** (`settle_time` s): `kp=0`, Passive `kd` - pure damping bleeds momentum from the RL gait. **Phase 2** (`duration` s): linearly interpolates leg joints from the settled pose to the FixStand sit target (`qs[1]`). Wheel joints (`kp=0`) damp to a stop and are skipped from interpolation. | Cutting directly from Velocity to a position target snaps the joints from mid-stride to a fixed target, throwing the robot sideways. The damping phase lets momentum die out first; the interpolation then eases the legs down smoothly - allowing the robot to go from Velocity to SitDown in a controlled manner without falling. |

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

`settle_time` and `duration` are configured in `config.yaml`'s `SitDown:` block:

```yaml
SitDown:
  settle_time: 0.25   # seconds of pure-damping before interpolation starts
  duration:    2.5   # seconds for the leg-joint interpolation to the sit pose
```

#### B2W-specific files

`deploy/robots/b2w/` was copied from `deploy/robots/b2/` and extended to support the four wheel joints. The B2 controller handles 12 DOF with pure position PD; B2W adds 4 velocity-controlled wheels on top, which required changes to the config arrays, the control loop, and the observation set. The shared DDS IDL and FSM structure are identical to B2.

##### 4. `deploy/robots/b2w/config/config.yaml`

`dds_domain_id` added (both sim and real robot use 0). All joint arrays extended from 12 → 16 entries for the wheels. `keyboard_transitions` added to every FSM state. A `SitDown` state added for a graceful sit-down before going limp (absent in b2). `policy_dir` points at the b2w rough log root.

```diff
+dds_domain_id: 0

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
+    kp: [400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400]
+    kd: [  8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8,   8]
   Velocity:
+    keyboard_transitions:
+      SitDown: "x"
-    policy_dir: ../../../logs/rsl_rl/unitree_b2_velocity
+    policy_dir: ../../../../robot_lab/logs/rsl_rl/unitree_b2w_rough
+  SitDown:
+    settle_time: 0.5
+    duration: 2.5
```

##### 5. `deploy/robots/b2w/main.cpp`

`dds_domain_id` read from config. Keyboard initialised (b2 leaves it `nullptr`). `State_SitDown` included.

```diff
+#include "FSM/State_SitDown.h"

-std::shared_ptr<Keyboard> FSMState::keyboard = nullptr;
+std::shared_ptr<Keyboard> FSMState::keyboard = std::make_shared<Keyboard>();

-unitree::robot::ChannelFactory::Instance()->Init(0, vm["network"].as<std::string>());
+unitree::robot::ChannelFactory::Instance()->Init(
+    param::config["dds_domain_id"].as<int>(), vm["network"].as<std::string>());
```

##### 6. `deploy/robots/b2w/src/State_RLBase.cpp`

Two additions over b2:

**`keyboard_velocity_commands` observation** - maps WASD/QE/arrows/numpad to `[lin_vel_x, lin_vel_y, ang_vel_z]`. Activated in `deploy.yaml` by using `keyboard_velocity_commands` as the observation key instead of `velocity_commands`, replacing the gamepad for sim2sim.

```diff
+REGISTER_OBSERVATION(keyboard_velocity_commands)
+{
+    // w/up/8=fwd, s/down/2=back, a/4=left, d/6=right, q/left/7=yaw-CCW, e/right/9=yaw-CW
+    ...
+}
```

**Hybrid control loop** - b2 sends all joints as position PD; b2w splits into legs `[0,12)` position PD and wheels `[12,16)` velocity control (`kp=0`, `kd=KD_WHEEL=1.0`). `processed_actions()` already applies `scale=5.0` - do not multiply again.

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

**`deploy.yaml` path** changed from per-run `params/deploy.yaml` (b2) to the shared `config/deploy.yaml`.

```diff
-YAML::LoadFile(policy_dir / "params" / "deploy.yaml")
+YAML::LoadFile(param::config_dir / "deploy.yaml")
```

##### 7. `deploy/robots/b2w/config/deploy.yaml` - NEW (does not exist in b2)

B2 loads `deploy.yaml` from inside each training run's `params/` folder. B2W centralises it at `config/deploy.yaml`, shared across all runs. Key additions over a typical b2 deploy.yaml:

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

### Prerequisite Installation

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

> **Note:** Installing to `/opt/unitree_robotics` instead of `/usr/local` means the SDK headers
> are not on GCC's default search path. The b2w `CMakeLists.txt` already accounts for this with
> an explicit `include_directories(/opt/unitree_robotics/include)` and
> `link_directories(/opt/unitree_robotics/lib)`. Other robots (b2, go2, etc.) would need the
> same addition if built on this machine.

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

### Check this before running sim2sim

#### `unitree_mujoco/simulate/config.yaml`

```yaml
robot: "b2w"          # ← change from "go2"
domain_id: 0
interface: "lo"       # loopback for sim2sim
use_joystick: 0       # 0 = no USB gamepad required (keyboard mode)
```

#### MJCF model

Confirm `unitree_mujoco/unitree_robots/b2w/` exists and contains `b2w.xml`.
If absent, obtain from the Unitree MuJoCo model pack.

**Verified actuator order in b2w.xml** (matches training order - no permutation needed):
```
[0]  FR_hip   [1]  FR_thigh  [2]  FR_calf
[3]  FL_hip   [4]  FL_thigh  [5]  FL_calf
[6]  RR_hip   [7]  RR_thigh  [8]  RR_calf
[9]  RL_hip   [10] RL_thigh  [11] RL_calf
[12] FR_foot  [13] FL_foot   [14] RR_foot  [15] RL_foot
```

#### ONNX policy file

After training and play have run, your `policy.onnx` will be at:

```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/exported/
```

If you want, just check that `policy_dir` in
`unitree_rl_lab/deploy/robots/b2w/config/config.yaml` is correct:

```yaml
    policy_dir: ../../../../robot_lab/logs/rsl_rl/unitree_b2w_rough
```

### Terrain Generation

The simulator ships with a flat ground scene (`scene.xml`) for each robot. Use the terrain
generator tool to produce a `scene_terrain.xml` that adds obstacles, rough ground, or Perlin
heightfields. Switching between them is a one-line change in `config.yaml`.

#### Prerequisites (once)

```bash
python3 -m pip install noise opencv-python-headless --break-system-packages
```

> The system Python on Ubuntu 24.04 is externally-managed; `--break-system-packages` is
> safe for these small packages.

#### Generate terrain

The terrain generator script (`terrain_tool/terrain_generator.py`) hardcodes `INPUT_SCENE_PATH = "./scene.xml"`, which is the go2 template. Running it unmodified will produce a `scene_terrain.xml` that references `go2.xml`, causing MuJoCo to fail with `XML Error: Error opening file '.../b2w/go2.xml'`.

The reliable approach is to run the generator and then patch the output:

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
# Flat ground (default):
robot_scene: "scene.xml"

# Terrain:
robot_scene: "scene_terrain.xml"
```

Then restart `./unitree_mujoco`.

#### Available terrain functions

| Function | Description | Key parameters |
|----------|-------------|----------------|
| `AddRoughGround` | Random cube field | `nums=[N,N]` grid, `box_size`, `box_euler_rand` for tilt |
| `AddPerlinHeighField` | Smooth undulating surface via Perlin noise | `size`, `height_scale`, `smoothness` |
| `AddStairs` | Ascending staircase | `width`, `height`, `stair_nums` |
| `AddSuspendStairs` | Floating stairs with gaps | `gap` |
| `AddBox` | Single box obstacle | `position`, `euler`, `size` |
| `AddGeometry` | sphere, cylinder, capsule, etc. | `geo_type` |
| `AddHeighFieldFromImage` | Terrain from a grayscale image | `input_img`, `height_scale` |

### Switching to Gamepad

To use a physical USB gamepad (or the unitree_mujoco software joystick) instead of keyboard
velocity commands:

**In `b2w/config/deploy.yaml`**:
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

**In `simulate/config.yaml`**:
```yaml
use_joystick: 1   # requires USB gamepad at /dev/input/js0
```

FSM transitions (Passive↔FixStand↔Velocity) still work via gamepad buttons even in keyboard
mode, because the `transitions` (DDS joystick) and `keyboard_transitions` blocks coexist.

---

## Workflow

Train a locomotion policy in Isaac Lab, watch it in the Isaac Sim GUI, export it to ONNX, and validate it in MuJoCo sim2sim.

### Step 1 - Train in Isaac Lab

Open a terminal and set up the Isaac Lab Python environment first.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
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

Checkpoints are saved to:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/
```

Training saves a checkpoint every 100 iterations. Ctrl+C is safe to interrupt between saves.
If the machine goes to sleep, training pauses and resumes on wake (the process stays alive).

### Step 1b - Watch the Robot Walk in Isaac Sim

Use `play.py` to load a checkpoint and watch the robot in the Isaac Sim GUI. Key flags:

- `--task` - environment to load (same as training).
- `--load_run <timestamp>` - load a specific run; omit to auto-load the most recent.
- `--num_envs 1` - spawn a single robot; omit for multiple parallel environments (no keyboard then).
- `--keyboard` - steer interactively; omit to send random velocity commands automatically.

#### Check how many iterations you have

```bash
ls /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/
# look for model_<N>.pt - the highest N is the last saved iteration
```

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

> Remove `--load_run` to auto-load the most recent run, or omit `--num_envs 1` to spawn multiple parallel environments (no keyboard in that case).

#### Keyboard controls

| Key | Action |
|---|---|
| Numpad 8 | Forward |
| Numpad 2 | Backward |
| Numpad 4 | Strafe left |
| Numpad 6 | Strafe right |
| Numpad 7 | Rotate left |
| Numpad 9 | Rotate right |
| L | Reset velocity to zero |

### Step 2 - Export to ONNX

Running `play.py` auto-exports `policy.onnx` into an `exported/` subfolder next to the loaded checkpoint.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless
```
> Can **Ctrl+C** if it runs successfully without crashing.

<details>
<summary><strong>Export from a specific run</strong></summary>

```bash
setup_isaaclab
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless \
  --load_run 2026-05-24_05-47-04
```
</details>

The exported policy will be at:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/exported/policy.onnx
```

### Step 3 - Sim2Sim in MuJoCo

Run the exported ONNX policy against the MuJoCo simulator over DDS on loopback.
No physical robot or gamepad required - control is via keyboard.

> **First time only:** complete the one-time setup, build, and `simulate/config.yaml` config
> under [MuJoCo Sim2Sim Validation Setup](#mujoco-sim2sim-validation-setup) - system packages, `unitree_sdk2`,
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

| Step | Key | Result |
|------|-----|--------|
| 1 | *(wait)* | Robot spawns limp in Passive state |
| 2 | `f` | Stands up (FixStand, ~3 s) |
| 3 | `r` | Policy activates (Velocity mode) |
| 4 | `w` / `s` / `a` / `d` | Forward / backward / strafe left / right |
| 5 | `q` / `e` | Yaw CCW / CW |
| 6 | `x` | Return to sitdown |

Velocity commands use the WASD keys (`w`/`s`/`a`/`d`) plus `q`/`e` for yaw.

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

> **When to update deploy.yaml:** the file content is determined by `rough_env_cfg.py`. As
> long as you retrain the same task without changing observation terms, scales, or the
> action structure, `config/deploy.yaml` works for every run. If you change the obs layout
> (add/remove terms, change scales), update `config/deploy.yaml` to match before running.

### Step 3b - Generate rough terrain

Check how to set it up under [B2W MuJoCo Sim2Sim Validation → Terrain Generation](#terrain-generation).

> The terrain generator supports: rough ground (random cubes), Perlin heightfield, stairs,
> floating stairs, arbitrary boxes and geometry.

---

## Rough Terrain Curriculum Training on Isaac-Sim

This section covers how the default rough terrain configuration trains the B2W inside **Isaac-Sim** using Isaac Lab, and how to develop new terrain variants. All training runs in the Isaac-Sim GPU-accelerated physics environment with 4096 parallel environments. The existing `v0` task defines the terrain mix, curriculum, and rewards - understanding it is the starting point for creating a `v1` with different obstacles or difficulty ranges.

### Training Command

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0
```

---

### Sub-Terrains

The environment generates a grid of terrain tiles using `ROUGH_TERRAINS_CFG` (defined in `isaaclab/terrains/config/rough.py`). Six terrain types are mixed together, each assigned a proportion of the total columns:

| Terrain Type | Proportion | Difficulty Parameter | Description |
|---|---|---|---|
| `pyramid_stairs` | 20% | step height: 5 cm → 23 cm | Ascending pyramid of steps - robot must climb up and over |
| `pyramid_stairs_inv` | 20% | step height: 5 cm → 23 cm | Descending inverted pyramid - robot must step down into a pit |
| `boxes` | 20% | box height: 5 cm → 20 cm | Grid of randomly-sized raised blocks spread across the tile |
| `random_rough` | 20% | noise amplitude: 2 cm → 10 cm | Heightfield with random uniform noise - uneven bumpy ground |
| `hf_pyramid_slope` | 10% | slope angle: 0° → ~22° | Smooth pyramid ramp - robot must navigate a continuous slope |
| `hf_pyramid_slope_inv` | 10% | slope angle: 0° → ~22° | Inverted smooth pyramid - robot must descend into a concave slope |

Each tile is **8 m × 8 m**. The full terrain grid is **10 rows × 20 columns**, giving 200 tiles in total. The difficulty parameter for each terrain type scales **linearly from its minimum to its maximum** across the 10 rows - row 0 has the easiest version of each terrain, row 9 has the hardest.

**4096 parallel environments** run simultaneously in simulation, collecting experience in parallel each step. This gives a large, diverse batch of transitions for each policy update.

---

### Terrain Difficulty Curriculum

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

`max_init_terrain_level = 5` is set in the scene config, so no robot starts on the hardest half of the terrain grid. The upper levels (6–9) are unlocked only through earned progression during training.

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

A robot that beats the hardest level (row 9) is sent to a **random level** rather than back to level 0, ensuring it continues to see a variety of difficulties.

#### Summary of the full training loop

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

### Implementing different terrain config (To be implemented)

I looked into whether there are any other rough terrain environments for me to train the robot in, but I think there is only one.

Normally, when I train, I pass in the `--task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0` flag to define the environment to train in. But based on what is in the `__init__.py` file for B2W, it looks like they only have environments registered for one type of rough terrain environment, which is established in `rough_env_cfg.py`.

So I think if we want to modify the rough terrain, we can create a separate `rough_env_cfg_v1.py` (for example) with some modified parameters, and create a new `gym.register(...)` entry with a different id (like `RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1`). We could then select it at training time with `--task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v1`, leaving the original `-v0` untouched.

> **Note:** This is not yet implemented - to be tested later to confirm it works.

---

## Skills Trained On

This section tracks which skills the policy has been trained on and which are planned next.

### Successfully trained on

**Velocity-tracking locomotion on rough terrain, via a terrain-difficulty curriculum.** The policy is commanded to track body velocities (`±1 m/s` linear, `±1 rad/s` angular) and learns to do so across a mix of terrains that get progressively harder as the policy improves.

**Sub-terrains.** The environment generates a 10-row × 20-column grid of 8 m × 8 m tiles (200 tiles) using `ROUGH_TERRAINS_CFG`. Six terrain types are mixed, each taking a share of the columns, and each type's difficulty parameter scales linearly across the 10 rows (row 0 easiest, row 9 hardest):

| Terrain Type | Proportion | Difficulty range |
|---|---|---|
| `pyramid_stairs` (ascending) | 20% | step height 5 cm → 23 cm |
| `pyramid_stairs_inv` (descending) | 20% | step height 5 cm → 23 cm |
| `boxes` (raised blocks) | 20% | box height 5 cm → 20 cm |
| `random_rough` (noisy heightfield) | 20% | noise 2 cm → 10 cm |
| `hf_pyramid_slope` (smooth ramp) | 10% | slope 0° → ~22° |
| `hf_pyramid_slope_inv` (concave ramp) | 10% | slope 0° → ~22° |

**Training method.** RSL-RL PPO with an actor-critic, running **4096 parallel environments**. The actor sees proprioception + velocity commands and outputs joint-position (legs) and wheel-velocity targets; the critic estimates value for GAE and is discarded after training.

**Terrain-difficulty curriculum** (`terrain_levels_vel`). Tiles are arranged in ascending difficulty across rows rather than randomly. The mechanics:

- **Initial placement:** each of the 4096 envs starts at a random level 0–5 (`max_init_terrain_level = 5`), so no robot begins on the hardest half - levels 6–9 are unlocked only by earned progression.
- **Promote / demote (per env, every episode end):** measure straight-line distance travelled from spawn. Walked > 4 m (half a tile) → **promote** one level; walked < 50% of what the commanded velocity required → **demote** one level; in between → no change. This is vectorised across all 4096 envs, no per-robot loop.
- **Respawn:** on the next reset the robot is teleported to a tile at its new level. A robot that clears the hardest row (9) is sent to a *random* level rather than back to 0, so it keeps seeing variety.

Because each env tracks its own level, the population naturally spreads across the difficulty range - most envs sit low early in training, and the distribution shifts upward as the policy improves.

**Velocity-command curriculum - disabled for B2W.** The framework can also start the commanded velocity range at 10% of max and widen it as tracking improves, but for B2W this is turned off (`command_levels_lin_vel = None`, `command_levels_ang_vel = None`). The robot is commanded across the full velocity range from episode one; only *terrain* difficulty is gated.

### What we want to train on next

All of the following reuse the existing velocity env (`RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0`) and need **config-only changes** - no new task definitions or algorithms.

| Skill | How | Why useful |
|---|---|---|
| **Flat high-speed driving** | Already registered: `RobotLab-Isaac-Velocity-Flat-Unitree-B2W-v0`. Widen `commands.base_velocity.ranges.lin_vel_x` (the commented `(-2.0, 2.0)` lines in `rough_env_cfg.py`) | Exploits the wheels - fast, efficient rolling that legs-only robots can't do |
| **Stair / curb / slope climbing** | Bias the terrain generator toward stairs + pyramids + gaps and let the terrain curriculum ramp difficulty | The headline wheeled-legged advantage: roll on flat, *step* over obstacles |
| **Rock-solid stand-still (no drift)** | Increase the `stand_still` reward weight in `rough_env_cfg.py` + zero-command holding | Directly targets command-following drift at zero command - useful as its own objective |
| **Payload robustness / push recovery** | Base + link mass are already randomized in `rough_env_cfg.py`; add external-force push events and heavier payload ranges | Carrying loads + surviving shoves = real-world deployment readiness |
| **Energy-efficient locomotion** | Raise `joint_power` / `wheel_vel_penalty` reward weights | Minimizes cost-of-transport → battery life |
| **Gait shaping** (trot/pace, or wheel-vs-step mode) | `feet_gait`, `feet_air_time` rewards (currently `feet_gait.weight = 0`) | Cleaner, more natural or task-specific gaits |
| **Posture / ride-height control** | `base_height_l2` target height | Crouch under obstacles, raise to clear |

## Deriving π in RL

### Defining Q-function

$$R_t = r_t + \gamma r_{t+1} + \gamma^2 r_{t+2} + \ldots$$

Total reward, $R_t$, is the discounted sum of all rewards obtained from time $t$. $\gamma$ is the discount factor that basically just means future reward not as "rewarding" as current reward.

$$Q(s_t, a_t) = \mathbb{E}[R_t \mid s_t, a_t]$$

Q-function captures the expected total future reward an agent in state $s$ can receive by executing a certain action, $a$.

Ultimately the agent needs a **policy** $\mathbf{\pi(s)}$, to infer the **best possible action** to take at its state $s$. [i.e. choose the action that maximises future reward]

$$\pi^*(s) = \underset{a}{\arg\max}\, Q(s,a)$$

---

## Proximal Policy Optimisation: PPO

PPO is an on-policy actor-critic policy gradient method. *(called **Proximal** because new policy is kept in the **proximity** of the old one)*

- The **actor** is a stochastic policy $\pi_\theta(a \mid s)$.
- The **critic** $V_\phi(s)$ estimates the state value.

Given that the probability ratio between candidate and data-collecting policies:

$$r_t(\theta) = \frac{\pi_\theta(a_t \mid s_t)}{\pi_{\theta_{old}}(a_t \mid s_t)}$$

### Hyperparameters

Every PPO hyperparameter referenced below is defined in one file,
`robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/agents/rsl_rl_ppo_cfg.py`
(class `UnitreeB2WRoughPPORunnerCfg`).

| Parameter | Value | File | Belongs to |
|---|---|---|---|
| `init_noise_std` | `1.0` | `rsl_rl_ppo_cfg.py` | Policy (actor) - initial action std $\sigma$ |
| `num_steps_per_env` | `24` | `rsl_rl_ppo_cfg.py` | Rollout - steps collected per env per iteration |
| `num_learning_epochs` | `5` | `rsl_rl_ppo_cfg.py` | Update loop - epochs over the (stale) batch |
| `num_mini_batches` | `4` | `rsl_rl_ppo_cfg.py` | Update loop - minibatches per epoch |
| `clip_param` | `0.2` | `rsl_rl_ppo_cfg.py` | [Clipped Surrogate Objective](#clipped-surrogate-objective) ($\varepsilon$); also clips the [Value Loss](#value-critic-loss) |
| `value_loss_coef` | `1.0` | `rsl_rl_ppo_cfg.py` | [Value (Critic) Loss](#value-critic-loss) - coefficient $c_v$ in the [combined loss](#the-combined-ppo-loss) |
| `use_clipped_value_loss` | `True` | `rsl_rl_ppo_cfg.py` | [Value (Critic) Loss](#value-critic-loss) - enables the pessimistic clipped critic loss |
| `entropy_coef` | `0.01` | `rsl_rl_ppo_cfg.py` | [Entropy Bonus](#entropy-bonus) - coefficient $c_e$ in the [combined loss](#the-combined-ppo-loss) |
| `gamma` | `0.99` | `rsl_rl_ppo_cfg.py` | [GAE](#generalised-advantage-estimation-gae) - reward discount $\gamma$ |
| `lam` | `0.95` | `rsl_rl_ppo_cfg.py` | [GAE](#generalised-advantage-estimation-gae) - baseline-trust factor $\lambda$ |
| `learning_rate` | `1.0e-3` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#adaptive-kl-based-learning-rate-schedule) - initial LR |
| `schedule` | `"adaptive"` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#adaptive-kl-based-learning-rate-schedule) |
| `desired_kl` | `0.01` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#adaptive-kl-based-learning-rate-schedule) - target KL per update |
| `max_grad_norm` | `1.0` | `rsl_rl_ppo_cfg.py` | [Applying the gradients](#applying-the-gradients) - gradient-norm clip |

> **NOTE:** $\gamma$ is the reward discount, while $\lambda$ separately controls how much the value baseline is trusted.

### The Combined PPO Loss

**The combined PPO loss** is implemented verbatim in the RSL-RL source as:

```python
loss = surrogate_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy.mean()
```

$$L = L^{\text{policy}} + c_v\, L^V - c_e\, H(\pi_\theta).$$

The coefficient $c_v$ is `value_loss_coef` and $c_e$ is `entropy_coef` (see [Hyperparameters](#hyperparameters)).

### Clipped Surrogate Objective

**Clipped Surrogate Objective** is:

$$L^{CLIP}(\theta) = \widehat{\mathbb{E}}_t\left[\min\left(\underbrace{r_t(\theta)\widehat{A}_t}_{unclipped},\ \underbrace{\mathrm{clip}(r_t(\theta), 1-\varepsilon, 1+\varepsilon)\widehat{A}_t}_{clipped}\right)\right]$$

CPO is asking how far I can trust this batch of data to tell me how to change the policy. This is done by basically:

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

Here $\varepsilon$ is `clip_param` (see [Hyperparameters](#hyperparameters)).

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

3. **Opimizer overshoot:** Momentum, learning rate, and the curvature of the loss surface mean a gradient step can overshoot.

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

### Value (Critic) Loss

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

### Entropy Bonus

**Entropy Bonus** measures how spread out the policy's action distribution is.

For Gaussian locomotion policy, entropy is a direct function of the action standard deviation:

- **High std**: Policy is exploring a wide range of actions
- **Low std**: Policy is deterministic and committed.

So Entropy bonus encourages exploration by rewarding higher policy entropy $H(\pi_\theta(\cdot \mid s))$.

**Code:** (comes from pytorch)

```python
entropy.mean()
```

### Generalised Advantage Estimation (GAE)

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

Here $\gamma$ is `gamma` and $\lambda$ is `lam` (see [Hyperparameters](#hyperparameters)).

### Adaptive KL-based learning-rate schedule

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

The target `desired_kl` is listed in [Hyperparameters](#hyperparameters).

**Essentially**: *It acts as a soft trust region complementing the clip, keeping each update inside a stable policy-change budget regardless of reward scale.*

### On-Policy data is used

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

### Applying the gradients

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

---

## Code Walkthrough: train.py

### PPO

From `train.py`,

1. Line 88:

   ```python
   from rsl_rl.runners import DistillationRunner, OnPolicyRunner
   ```

2. Line 205-206:

   ```python
   if agent_cfg.class_name == "OnPolicyRunner":
       runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=log_dir, device=agent_cfg.device)
   ```

   - Line 39-40 of `on_policy_runner.py`:

     ```python
     # Create the algorithm
     alg_class: type[PPO] = resolve_callable(self.cfg["algorithm"]["class_name"])
     self.alg = alg_class.construct_algorithm(obs, self.env, self.cfg, self.device)
     ```

     1. Since `cfg["algorithm"]["class_name"] == "PPO"`, it then calls `PPO.construct_algorithm()` in `ppo.py`.
     2. Line 415-417, builds actor-critic class:

        ```python
        alg_class: type[PPO] = resolve_callable(cfg["algorithm"].pop("class_name")
        actor_class: type[MLPModel] = resolve_callable(cfg["actor"].pop("class_name"))
        critic_class: type[MLPModel] = resolve_callable(cfg["critic"].pop("class_name"))
        ```

     3. Lines 432-443 initialise the Actor, Critic, followed by RolloutStorage, and the PPO object which is the `self.alg`

3. If resume, previously trained model is loaded in, through Line 214-217:

   ```python
   if agent_cfg.resume or agent_cfg.algorithm.class_name == "Distillation":
       print(f"[INFO]: Loading model checkpoint from: {resume_path}")
       # load previously trained model
       runner.load(resume_path)
   ```

4. Line 224:

   ```python
   runner.learn(num_learning_iterations=agent_cfg.max_iterations, init_at_random_ep_len=True)
   ```

   a. Line 66 in `on_policy_runner` calls `train_mode()`, which is called on `ppo.py` as well:

      1. On `ppo.py`, both actor and critic are set to train, in Line 346-349:

         ```python
         def train_mode(self) -> None:
             """Set train mode for learnable models."""
             self.actor.train()
             self.critic.train()
         ```

         Note that the `train()` method here is from MLP library

   b. Line 76 – 105 is the entire training process.

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

   c. Subsequently in line 108, the `update()` function is called, which does the main loss calculation and backprop.

      ```python
      # Update policy
      loss_dict = self.alg.update()
      ```

---
