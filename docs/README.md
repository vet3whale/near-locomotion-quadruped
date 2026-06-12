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
    <li><a href="#32-code-changes-made">3.2 Code Changes Made</a></li>
    <li><a href="#33-prerequisite-installation">3.3 Prerequisite Installation</a></li>
    <li><a href="#34-check-this-before-running-sim2sim">3.4 Check this before running sim2sim</a></li>
    <li><a href="#35-terrain-generation">3.5 Terrain Generation</a></li>
    <li><a href="#36-switching-to-gamepad">3.6 Switching to Gamepad</a></li>
  </ul></details></li>
  <li><details><summary><a href="#4-workflow">4. Workflow</a></summary><ul>
    <li><a href="#41-step-1---train-in-isaac-lab">4.1 Step 1 - Train in Isaac Lab</a></li>
    <li><a href="#42-step-1b---watch-the-robot-walk-in-isaac-sim">4.2 Step 1b - Watch the Robot Walk in Isaac Sim</a></li>
    <li><a href="#43-step-2---export-to-onnx">4.3 Step 2 - Export to ONNX</a></li>
    <li><a href="#44-step-2a---evaluate-policies-cross-evaluation-matrix">4.4 Step 2a - Evaluate Policies (Cross-Evaluation Matrix)</a></li>
    <li><a href="#45-step-3---sim2sim-in-mujoco">4.5 Step 3 - Sim2Sim in MuJoCo</a></li>
    <li><a href="#46-step-3b---generate-rough-terrain">4.6 Step 3b - Generate rough terrain</a></li>
    <li><a href="#47-step-4---sim2real-to-be-tested">4.7 Step 4 - Sim2Real (to be tested)</a></li>
  </ul></details></li>
  <li><details><summary><a href="#5-rough-terrain-curriculum-training-on-isaac-sim">5. Rough Terrain Curriculum Training on Isaac-Sim</a></summary><ul>
    <li><a href="#51-training-command">5.1 Training Command</a></li>
    <li><a href="#52-sub-terrains-the-default-mix">5.2 Sub-Terrains (the default mix)</a></li>
    <li><a href="#53-terrain-difficulty-curriculum">5.3 Terrain Difficulty Curriculum</a></li>
    <li><a href="#54-plug-in-a-different-terrain">5.4 Plug in a different terrain</a></li>
    <li><a href="#55-choose-a-reward-tracking-method">5.5 Choose a reward tracking method</a></li>
    <li><a href="#56-worked-example-staircaseup-teacher">5.6 Worked example: StaircaseUp teacher</a></li>
  </ul></details></li>
  <li><details><summary><a href="#6-evaluation-matrix">6. Evaluation Matrix</a></summary><ul>
    <li><a href="#61-what-the-matrix-measures">6.1 What the Matrix Measures</a></li>
    <li><a href="#62-new-files">6.2 New Files</a></li>
    <li><a href="#63-changed-files">6.3 Changed Files</a></li>
  </ul></details></li>
  <li><details><summary><a href="#7-skills-trained-on">7. Skills Trained On</a></summary><ul>
    <li><a href="#71-successfully-trained-on">7.1 Successfully trained on</a></li>
    <li><a href="#72-what-we-want-to-train-on-next">7.2 What we want to train on next</a></li>
  </ul></details></li>
  <li><details><summary><a href="#8-challenges-faced">8. Challenges Faced</a></summary><ul>
    <li><a href="#81-fixstand-wheel-skid---bug-that-passed-in-sim-but-failed-on-the-real-robot">8.1 FixStand wheel skid - bug that passed in sim but failed on the real robot</a></li>
  </ul></details></li>
  <li><details><summary><a href="#9-deriving-π-in-rl">9. Deriving π in RL</a></summary><ul>
    <li><a href="#91-defining-q-function">9.1 Defining Q-function</a></li>
  </ul></details></li>
  <li><details><summary><a href="#10-proximal-policy-optimisation-ppo-teacher">10. Proximal Policy Optimisation: PPO (Teacher)</a></summary><ul>
    <li><a href="#101-hyperparameters">10.1 Hyperparameters</a></li>
    <li><a href="#102-the-combined-ppo-loss">10.2 The Combined PPO Loss</a></li>
    <li><a href="#103-clipped-surrogate-objective">10.3 Clipped Surrogate Objective</a></li>
    <li><a href="#104-value-critic-loss">10.4 Value (Critic) Loss</a></li>
    <li><a href="#105-entropy-bonus">10.5 Entropy Bonus</a></li>
    <li><a href="#106-generalised-advantage-estimation-gae">10.6 Generalised Advantage Estimation (GAE)</a></li>
    <li><a href="#107-adaptive-kl-based-learning-rate-schedule">10.7 Adaptive KL-based learning-rate schedule</a></li>
    <li><a href="#108-on-policy-data-is-used">10.8 On-Policy data is used</a></li>
    <li><a href="#109-applying-the-gradients">10.9 Applying the gradients</a></li>
    <li><a href="#1010-privileged-learning">10.10 Privileged Learning</a></li>
  </ul></details></li>
  <li><details><summary><a href="#11-distillation-using-dagger-student">11. Distillation using DAGGER (Student)</a></summary><ul>
    <li><a href="#111-teacher-student-distillation-training">11.1 Teacher-Student Distillation Training</a></li>
    <li><details><summary><a href="#112-dagger-dataset-aggregation">11.2 DAGGER (Dataset Aggregation)</a></summary><ul>
      <li><a href="#1121-behaviour-cloning">11.2.1 Behaviour Cloning</a></li>
      <li><a href="#1122-dagger">11.2.2 DAgger</a></li>
      <li><a href="#1123-rsl-rl-implementation-dagger">11.2.3 RSL-RL Implementation: DAgger</a></li>
    </ul></details></li>
  </ul></details></li>
  <li><details><summary><a href="#12-code-walkthrough-trainpy">12. Code Walkthrough: train.py</a></summary><ul>
    <li><a href="#121-ppo">12.1 PPO</a></li>
    <li><a href="#122-distillation-mlp-student">12.2 Distillation (MLP Student)</a></li>
    <li><a href="#123-distillation-lstm-student">12.3 Distillation (LSTM Student)</a></li>
  </ul></details></li>
</ul>

---
## 1. Repository Layout

**Key Folders:**
<details>
<summary><strong>Click to expand Key Folders: snippet</strong></summary>

```
near-locomotion-quadruped/
├── robot_lab/                                         ← train, eval & export (Isaac Lab)
│   ├── source/robot_lab/tasks/.../unitree_b2w/        ← task definitions (see note below)
│   │   ├── rough_env_cfg.py, flat_env_cfg.py          ← v0 rough & flat tasks
│   │   ├── staircaseup_teacher_env_cfg.py             ← stairs-climbing teacher terrain
│   │   ├── slopeup_teacher_env_cfg.py                 ← slope-climbing teacher terrain
│   │   ├── agents/rsl_rl_ppo_cfg.py                   ← PPO runner cfgs (per-experiment log dirs)
│   │   └── __init__.py                                ← gym.register task ids
│   └── scripts/reinforcement_learning/rsl_rl/
│       ├── train.py, play.py                          ← train, watch, export ONNX
│       ├── play_cs.py                                 ← USD-map play; --eval scores one matrix cell
│       └── eval_matrix.py                             ← driver that fills the cross-eval matrix
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

</details>

> **Note**: `source/robot_lab/tasks/.../unitree_b2w/` refers to `robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/`

---

## 2. Environment Setup

### 2.1 System Container Was Tested On

<details>
<summary><strong>Click to expand 2.1 System Container Was Tested On table</strong></summary>

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
<summary><strong>Click to expand table</strong></summary>

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

   Close the window when done. If it crashes on startup, check the NVIDIA driver version (see [System Container Was Tested On](#21-system-container-was-tested-on) - driver 595 is known broken).

### 2.4 Shell Functions

The dev container's `~/.bashrc` defines two functions. Call each once per terminal as needed:

| Function | When to call | What it does |
|---|---|---|
| `setup_isaaclab` | Before any Isaac Lab script (`train.py`, `play.py`) | Unsets `PYTHONPATH`, sources Isaac Sim's Python env, adds Isaac Lab + robot_lab packages to `PYTHONPATH`, and aliases `python`/`python3` to Python 3.11 |
| `sim2sim_env` | Before running `unitree_mujoco` or `b2w_ctrl` | Unsets ROS env vars that would interfere with DDS, sets `LD_LIBRARY_PATH` for the controller's shared libs, and sets the `CYCLONEDDS_URI` to disable Iceoryx (loopback sim2sim) |

### 2.5 Reference - `--load_actor_only` flag

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

The rough critic receives privileged observations, such as height scans, contact forces, terrain geometry, that flat critic doesn't need --> So never saw. 
`play.py` still looks for critic's input, so by passing in `--load_actor_only`, only actor with 57 base observations is used.

---

## 3. MuJoCo Sim2Sim Validation Setup

This section explains how to set up Sim2Sim validation using MuJoCo.

### 3.1 Overview

**Training policy location** (auto-selected by `parser_policy_dir`):
```
robot_lab/logs/rsl_rl/unitree_b2w_rough/<latest-timestamp>/
  exported/policy.onnx ← not committed to github; run play.py first to export it
```

**IMPORTANT**: Set which policy the controller deploys (for sim2sim or sim2real) by opening `unitree_rl_lab/deploy/robots/b2w/config/config.yaml` and editing `policy_dir` to point at the log root of the run you want. `parser_policy_dir` function in controller then automatically finds the most recent timestamp subdirectory that contains an `exported/` folder and loads `policy.onnx` from it.  

See [Step 2 - Export to ONNX](#43-step-2---export-to-onnx) for how to generate the ONNX file from a checkpoint using `play.py`.

**Shared deploy config** (loaded by the controller at startup): This is the yaml used when the robot is in Velocity state.
```
unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml  ← observation/action config (editable)
```

### 3.2 Code Changes Made

#### Shared headers (unitree_rl_lab)

These files are shared across all robots. Changes are backward-compatible and gated so
existing robots (b2, go2, h1, g1_29dof) are unaffected.

##### 1. `deploy/include/FSM/FSMState.h` - keyboard FSM transitions

| Action | Why |
|---|---|
| Added a `keyboard_transitions` parsing block immediately after the existing `transitions` block and before `// register for all states` (code below). | When `FSMState::keyboard` is `nullptr` (robots that don't initialize it in `main.cpp`), the block is skipped - so existing robots (b2, go2, h1, g1_29dof) are unaffected. Transitions are edge-triggered (`on_pressed`, not held), so a brief keypress advances the FSM. |

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

##### 2. `deploy/include/isaaclab/envs/mdp/observations/observations.h` - wheel-masked joint positions

| Action | Why |
|---|---|
| Added a generic observation `joint_pos_rel_without_wheel` between `joint_pos_rel` and `joint_vel_rel` (code below); wheel indices are read from `deploy.yaml`. | The B2W policy was trained with `joint_pos_rel_without_wheel`: a 16-element `q - q_default` vector where the four wheel slots [12–15] are forced to 0.0 - wheel position is undefined for continuously-spinning joints, so feeding the raw value there is wrong. Output length always equals the full joint count (16) to match the policy input dimension. |

<details>
<summary><strong>Click to expand CPP snippet</strong></summary>

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

</details>

The wheel indices are read from `deploy.yaml`:

```yaml
joint_pos_rel_without_wheel:
  params: {wheel_joint_ids: [12, 13, 14, 15]}
```

##### 3. `deploy/include/FSM/State_SitDown.h` - two-phase sit-down state

| Action | Why |
|---|---|
| New FSM state with two phases, then auto-transitions to Passive. **Phase 1** (`settle_time` s): `kp=0`, Passive `kd` - pure damping bleeds momentum from the RL gait. **Phase 2** (`duration` s): linearly interpolates leg joints from the settled pose to the FixStand sit target (`qs[1]`). Wheel joints (`kp=0`) damp to a stop and are skipped from interpolation. | Cutting directly from Velocity to a position target snaps the joints from mid-stride to a fixed target, throwing the robot sideways. The damping phase lets momentum die out first; the interpolation then eases the legs down smoothly - allowing the robot to go from Velocity to SitDown in a controlled manner without falling. |

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
  settle_time: 0.25   # seconds of pure-damping before interpolation starts
  duration:    2.5   # seconds for the leg-joint interpolation to the sit pose
```

#### B2W-specific files

`deploy/robots/b2w/` was copied from `deploy/robots/b2/` and extended to support the four wheel joints. The B2 controller handles 12 DOF with pure position PD; B2W adds 4 velocity-controlled wheels on top, which required changes to the config arrays, the control loop, and the observation set. The shared DDS IDL and FSM structure are identical to B2.

##### 4. `deploy/robots/b2w/config/config.yaml`

All joint arrays extended from 12 → 16 entries for the wheels. `keyboard_transitions` added to every FSM state. A `SitDown` state added for a graceful sit-down before going limp (absent in b2). `policy_dir` points at the b2w rough log root.

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

</details>

##### 5. `deploy/robots/b2w/main.cpp`

Keyboard initialised (b2 leaves it `nullptr`). `State_SitDown` included.

```diff
+#include "FSM/State_SitDown.h"

-std::shared_ptr<Keyboard> FSMState::keyboard = nullptr;
+std::shared_ptr<Keyboard> FSMState::keyboard = std::make_shared<Keyboard>();

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

##### 7. `deploy/robots/b2w/config/deploy.yaml` - NEW (does not exist in b2)

RobotLab training runs save their Isaac Lab/RSL-RL configs under each run's `params/` folder as
`env.yaml` and `agent.yaml`; they do **not** generate `deploy.yaml`.

`deploy.yaml` belongs to the separate `unitree_rl_lab` deployment stack. It is the hand-written
adapter that lets the Unitree C++ controller run a RobotLab-trained B2W policy by recreating the
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

### 3.3 Prerequisite Installation

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

### 3.4 Check this before running sim2sim

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

### 3.5 Terrain Generation

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

### 3.6 Switching to Gamepad

To use a physical USB gamepad (or the unitree_mujoco software joystick) instead of keyboard
velocity commands:

**In `b2w/config/deploy.yaml`**:
<details>
<summary><strong>Click to expand **In `b2w/config/deploy.yaml`** snippet</strong></summary>

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

---

## 4. Workflow

Train a locomotion policy in Isaac Lab, watch it in the Isaac Sim GUI, export it to ONNX, and validate it in MuJoCo sim2sim.

### 4.1 Step 1 - Train Teacher in Isaac Lab

Open a terminal and set up the Isaac Lab Python environment first.

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --headless --max_iterations 5000   # without --max_iterations it runs for 20000 iterations
```

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

Checkpoints are saved to:
```
/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/
```

Training saves a checkpoint every 100 iterations. Ctrl+C is safe to interrupt between saves.
If the machine goes to sleep, training pauses and resumes on wake (the process stays alive).

### 4.2 Step 1b - Watch the Robot Walk in Isaac Sim

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

---

### 4.3 Step 1c - Distillation (Student-Teacher)

Distillation produces a deployable student policy that uses only proprioceptive observations (no height scan, no linear velocity). Student learns to mimic it via MSE loss on its own on-policy rollouts.

#### Phase 1 - Train the teacher (PPO)

The teacher is the privileged PPO policy already trained in [Step 1](#step-1--train-in-isaac-lab) — no extra training is needed here. That checkpoint is reused as the frozen label source; pass its run timestamp to `--load_run` in the Phase 2 commands below.

#### Phase 2 - Distil teacher into student

The student can be one of two network types:

- **MLP** (`rsl_rl_distillation_cfg_entry_point`) = a plain feed-forward network. It maps the current single frame of observations straight to an action — no memory of previous steps.
- **LSTM** (`rsl_rl_distillation_recurrent_cfg_entry_point`) = a recurrent neural network (RNN), specifically the LSTM variety. It keeps a hidden state (`h`/`c`) that carries information across timesteps, so each action depends not just on the current frame but on the history of what it has seen.

#### Phase 2a - MLP distillation

Feed-forward student (single-frame observation, no memory):

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_cfg_entry_point \
  --load_run 2026-05-24_05-47-04 \
  --headless
```

`--load_run` is the **timestamp folder name only** (not the full path) from the Phase 1 PPO run. The script automatically looks in `logs/rsl_rl/unitree_b2w_rough/`.

##### Play / evaluate the MLP student

```bash
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_cfg_entry_point \
  --load_run 2026-05-29_07-07-23 \
  --keyboard
```

To load a specific checkpoint pass the **full absolute path**:

```bash
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_cfg_entry_point \
  --checkpoint /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/2026-05-29_07-07-23/model_500.pt \
  --keyboard
```

#### Phase 2b - LSTM distillation

Recurrent (LSTM) student. It carries a hidden state across timesteps, letting it implicitly estimate the linear velocity it cannot observe directly. This minimises the velocity drift as seen with feed-forward MLP student.  

```bash
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --load_run 2026-05-24_05-47-04 \
  --headless
```

> **Code additions for the LSTM student** : DOCUMENT CODE ADDITIONS HERE.

##### Play / evaluate the LSTM student

Use the **recurrent** agent so `play.py` rebuilds the LSTM and carries its hidden state across steps:

```bash
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --load_run 2026-05-29_07-07-23 \
  --keyboard
```

To load a specific checkpoint pass the **full absolute path**:

```bash
python scripts/reinforcement_learning/rsl_rl/play.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --checkpoint /workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/2026-05-29_07-07-23/model_500.pt \
  --keyboard
```

### Warm-start student from a previous distillation run (multi-task reuse)

Match the `--agent` to the network type of the student you are warm-starting — the `--load_student_run` checkpoint must come from a run with the same architecture.

MLP student:

```bash
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_cfg_entry_point \
  --load_run <new_ppo_run> \
  --load_student_run <prev_distillation_run> \
  --headless
```

LSTM student:

```bash
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0 \
  --agent=rsl_rl_distillation_recurrent_cfg_entry_point \
  --load_run <new_ppo_run> \
  --load_student_run <prev_distillation_run> \
  --headless
```


### 4.3 Step 2 - Export to ONNX

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

### 4.4 Step 2a - Evaluate Policies (Cross-Evaluation Matrix)

Once you have more than one trained policy (e.g. a staircase teacher, a slope teacher, the rough generalist, and eventually the distilled student), score **each policy on each terrain** to build a success-rate matrix - rows are terrains, columns are policies. One driver command fills the whole matrix:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/eval_matrix.py \
  --num_envs 512 --out_csv b2w_eval.csv --logger b2w-teacher-eval
```

What it does:

- **Rows (terrains):** the `StaircaseUp-Teacher`, `SlopeUp-Teacher`, and `Flat` tasks by default.
- **Columns (policies):** every `logs/rsl_rl/unitree_b2w_*` experiment that has a checkpoint, using each one's newest run + newest `model_<N>.pt`. The distilled-student column appears automatically once a `unitree_b2w_student` run exists.
- For each (terrain, policy) pair it spawns `--num_envs` robots, rolls out one episode, and records two numbers per cell: **success rate** (fraction that never triggered the fall termination) and **mean terrain level** (difficulty of the tiles the survivors held).
- Results accumulate into `--out_csv`; pass `--logger <project>` to also log the matrix as a wandb Table.

Each policy is loaded **actor-only**, so a teacher trained on one terrain still loads when evaluated on another (its critic, whose privileged-observation size differs per task, is skipped - only the actor runs at eval).

<details>
<summary><strong>Restrict the columns, or change the terrains</strong></summary>

```bash
# only specific policies (experiment names under logs/rsl_rl/, dirs, or direct .pt paths)
python scripts/reinforcement_learning/rsl_rl/eval_matrix.py \
  --policies unitree_b2w_staircaseup_teacher unitree_b2w_slopeup_teacher unitree_b2w_rough \
  --num_envs 512 --out_csv b2w_eval.csv

# different rows
python scripts/reinforcement_learning/rsl_rl/eval_matrix.py \
  --tasks RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0 \
          RobotLab-Isaac-Velocity-Flat-Unitree-B2W-v0
```
</details>

<details>
<summary><strong>Evaluate a single policy on a single terrain</strong></summary>

The driver just calls `play_cs.py --eval` once per cell. To fill one cell yourself:

```bash
python scripts/reinforcement_learning/rsl_rl/play_cs.py \
  --task=RobotLab-Isaac-Velocity-StaircaseUp-Teacher-Unitree-B2W-v0 \
  --headless --num_envs 512 --eval \
  --checkpoint logs/rsl_rl/unitree_b2w_staircaseup_teacher/<run>/model_<N>.pt \
  --out_csv b2w_eval.csv --logger b2w-teacher-eval
```

The row label comes from `--task`, the column label is auto-derived from the checkpoint's experiment-dir name.
</details>

### 4.5 Step 3 - Sim2Sim in MuJoCo

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
| 4 | `w` / `s` / `a` / `d` | Forward / backward / strafe left / right |
| 5 | `q` / `e` | Yaw CCW / CW |
| 6 | `x` | Return to sitdown |

</details>

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

### 4.6 Step 3b - Generate rough terrain

Check how to set it up under [B2W MuJoCo Sim2Sim Validation → Terrain Generation](#35-terrain-generation).

> The terrain generator supports: rough ground (random cubes), Perlin heightfield, stairs,
> floating stairs, arbitrary boxes and geometry.

---

### 4.7 Step 4 - Sim2Real (to be tested)

Following are the steps to deploy
`robot_lab/logs/rsl_rl/unitree_b2w_rough` onto the real robot - this should be a safe starting point to just walk.  

The controller binary, `deploy.yaml`, and FSM are **identical to sim2sim** - the same `b2w_ctrl`
you already ran against MuJoCo. Only two things change for hardware:

1. `policy_dir` in `config.yaml` points at the rough-policy log root (already the default).
2. `b2w_ctrl` runs on the robot's real network interface instead of `lo`.


The E-Stop Button is **X** on the laptop, after deploying the policy.

#### Prerequisites

- `b2w_ctrl` already builds and runs cleanly in [sim2sim](#45-step-3---sim2sim-in-mujoco) (so the
  controller, `unitree_sdk2`, and the ONNX Runtime symlink are all set up).
- The physical B2W is powered on and sitting on the ground. It does not need to be put in any
  special low-level mode - the controller claims the motor channel on startup, and `f` stands it up.

#### 1. Export the rough policy to ONNX

To deploy onto the robot, need `.onnx` format file.
See [Step 2 - Export to ONNX](#43-step-2---export-to-onnx) for details.

#### 2. Confirm the controller points at the rough logs

In [`unitree_rl_lab/deploy/robots/b2w/config/config.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/config.yaml),
`policy_dir` under the `Velocity` state should be the rough log root:

```yaml
  Velocity:
    policy_dir: ../../../../robot_lab/logs/rsl_rl/unitree_b2w_rough
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
| 4 | `w` / `s` / `a` / `d` | Forward / backward / strafe left / right |
| 5 | `q` / `e` | Yaw CCW / CW |
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
| Leg hold gains (FixStand) | [`config.yaml`](../unitree_rl_lab/deploy/robots/b2w/config/config.yaml) `FixStand.kp`/`kd` | `400` / `8` | Wheel slots [12-15] are `kp=0` here - see [§8.1](#81-fixstand-wheel-skid---bug-that-passed-in-sim-but-failed-on-the-real-robot) |

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
   Jetson, and copy the `unitree_b2w_rough` log dir across so `policy_dir` resolves locally.
2. Launch on the Jetson with `--network <jetson NIC on 192.168.123.0/24>`. Once it is running the
   tether can be unplugged - the controller lives entirely on the robot.
3. Drive with the wireless remote instead of the keyboard: switch the velocity observation from
   keyboard to gamepad as in [Switching to Gamepad](#36-switching-to-gamepad). The FSM transitions
   (FixStand / Velocity / SitDown) already work from the gamepad buttons.


---

## 5. Rough Terrain Curriculum Training on Isaac-Sim

Every B2W terrain policy is defined by **two independent choices** that you mix and match:

| Choice | What it controls | Options | Where |
|---|---|---|---|
| **Terrain** | the obstacles the robot trains on | stairs, slopes, boxes, rough ground, ... | [5.4](#54-plug-in-a-different-terrain) |
| **Reward tracking** | how the robot is scored | velocity tracking or position tracking | [5.5](#55-choose-a-reward-tracking-method) |

The default `v0` task is **mixed rough terrain + velocity tracking**. To build a new variant you swap the terrain ([5.4](#54-plug-in-a-different-terrain)), the reward method ([5.5](#55-choose-a-reward-tracking-method)), or both. [5.6](#56-worked-example-staircaseup-teacher) is a full worked example that does both (staircase terrain + position tracking).

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

A terrain variant is just a new `TerrainGeneratorCfg` wired into a subclass of the rough env. You never edit `v0` - you create a parallel task that reuses everything except the terrain. The recipe is four files; each one is a small, self-contained addition.

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
<summary><strong>Click to expand PYTHON snippet</strong></summary>

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

</details>

> **Note on `gpu_collision_stack_size`:** terrains with many discrete surfaces (stepping stones, gap, repeated objects) generate far more collision contacts than smooth terrains. If you see `PhysX error: collisionStackSize buffer overflow` at runtime, add `self.sim.physx.gpu_collision_stack_size = 2**27` to `__post_init__` to raise the GPU buffer from the default 64 MB to 128 MB.

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

### 5.5 Choose a reward tracking method

This is the second choice. It decides **what the robot is rewarded for**, independent of the terrain. Both methods use the same robot, terrain, and difficulty curriculum - only the command input and the tracking reward differ:

| | Velocity tracking | Position tracking |
|---|---|---|
| **Command** | `base_velocity` (x/y/yaw velocity) | `pose_command` (a 2D pose goal) |
| **Rewards** | `track_lin_vel_xy_exp`, `track_ang_vel_z_exp` | `move_to_goal`, `position_tracking_fine`, `heading_tracking` |
| **Robot must** | match a commanded speed every step | reach a goal, choosing its own speed |
| **Best for** | general locomotion, slopes, flat driving | stairs, steps, parkour obstacles |
| **Deploy** | drive directly with a velocity stick | needs a pose-goal source / planner |

Use **velocity tracking** for the generalist policy you actually deploy. Use **position tracking** for hard obstacle teachers that need freedom to slow down, lift, recover, and continue.

#### Velocity tracking

Uses `base_velocity` commands and rewards the robot for matching the commanded `x/y/yaw` velocity:

```python
track_lin_vel_xy_exp
track_ang_vel_z_exp
```

Good for general rough-terrain locomotion, since the deployed robot is driven by velocity commands. Less ideal for tall stairs: the robot may need to slow down, bump a riser, lift, recover, then continue - strict velocity tracking can punish those useful climbing motions.

#### Position tracking

The position teacher removes `base_velocity` and gives the robot a sampled 2D pose goal instead:

```python
move_to_goal
position_tracking_fine
heading_tracking
```

Treats stair climbing like navigation. The robot is rewarded for reaching an outward goal, so it chooses its own speed while climbing instead of holding a fixed velocity through every contact. The better fit for 30 cm stairs and parkour-like obstacles.

Position tracking now lives in its **own package** rather than being bolted onto the velocity task. The old bolted-on version trained unstably - the robot's motions got noisier and noisier until the policy fell apart - because a pose goal is a softer signal than a velocity command. The dedicated package fixes that with `move_to_goal` ([`move_toward_goal_exp`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/mdp/rewards.py)), a dense goal-directed reward that stays graded everywhere and so keeps the action distribution bounded the way velocity tracking does.

#### Code Changes

The entire [`velocity`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/) package was copied verbatim into a new B2W [`position`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/) package; only the base env config and the B2W weights then changed. The robot, physics, sensors, domain randomisation, and PPO network stay identical. The [`position/mdp/`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/mdp/) helpers are a straight copy of [`velocity/mdp/`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/) plus one added reward, [`move_toward_goal_exp`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/mdp/rewards.py).

<details>
<summary><strong>Exact differences: velocity vs position config</strong></summary>

**Base env config** ([`velocity_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/velocity_env_cfg.py) -> [`position_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/position_env_cfg.py)):

| Item | Velocity | Position |
|---|---|---|
| Command | `base_velocity` (x/y/yaw velocity, resample 10 s) | `pose_command` (2D pose goal, `+/-5 m`, resample 20 s) |
| Command observation | `velocity_commands` | `pose_commands` |
| Tracking rewards | `track_lin_vel_xy_exp`, `track_ang_vel_z_exp` | `move_to_goal` (dense drive), `position_tracking` / `position_tracking_fine` (tanh approach / settle), `heading_tracking` |
| Command-gated terms | keyed on `base_velocity` | repointed to `pose_command` (`stand_still`, `joint_pos_penalty`, `feet_height_body`, `feet_contact_without_cmd`, `feet_air_time`, `feet_gait`) |
| Terrain curriculum | `terrain_levels_vel` + `command_levels_lin/ang_vel` | `terrain_levels_pose` (no command-level curricula) |

The only new function is [`move_toward_goal_exp`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/mdp/rewards.py); the tanh pose terms [`position_command_error_tanh`](../../isaaclab/source/isaaclab_tasks/isaaclab_tasks/manager_based/navigation/mdp/rewards.py) and [`heading_command_error_abs`](../../isaaclab/source/isaaclab_tasks/isaaclab_tasks/manager_based/navigation/mdp/rewards.py) are imported from IsaacLab's navigation mdp. `terrain_levels_pose` is defined at the top of [`position_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/position_env_cfg.py).

**B2W weights** ([`rough_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/config/wheeled/unitree_b2w/rough_env_cfg.py)): after the velocity-mirror tuning the two configs sit close together -

| Item | Velocity | Position |
|---|---|---|
| Dense tracking weights | `track_lin_vel_xy_exp` 3.0, `track_ang_vel_z_exp` 1.5 | `move_to_goal` 5.0, `position_tracking_fine` 5.0, `heading_tracking` -0.5 (coarse `position_tracking` off) |
| `is_terminated` penalty | 0 | 0 |
| `illegal_contact` termination | None | None |
| `bad_orientation` termination | (never present) | None (disabled) |
| Spawn roll / pitch | `+/-3.14` (self-rights from any pose) | `+/-0.5` (near-upright) |

</details>

New task id: `RobotLab-Isaac-Position-StaircaseUp-Unitree-B2W-v0`. The staircase task [`staircaseup_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/config/wheeled/unitree_b2w/staircaseup_env_cfg.py) just swaps in the stair terrain plus a few climbing tweaks.

Why it is stable: [`move_toward_goal_exp`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/mdp/rewards.py) gives a gradient everywhere (the tanh terms go flat far from the goal), so it bounds the action distribution the way velocity tracking does - no fall penalty needed. An earlier dedicated-package version kept a large `is_terminated` penalty for that tightness instead, but it trained timidly and the terrain curriculum stalled around level 2; removing the penalty and adding the dense drive let it climb past that.

#### Tuning & extensibility

For a new terrain (stepping stones, slope, gaps) you usually **do not touch the reward system at all**. Copy [`staircaseup_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/config/wheeled/unitree_b2w/staircaseup_env_cfg.py) and change four things:

1. **The terrain** - swap the terrain generator for your obstacle. (Main change.)
2. **Foot clearance** - `feet_height_body` `target_height`/weight: more lift for tall steps, less for slopes.
3. **Climbing vs smoothness** - loosen `action_rate_l2`, `joint_pos_penalty`, `lin_vel_z_l2` and lower `upward` to climb hard; tighten them for a smooth gait on slopes.
4. Register the task id + add a one-line PPO config (experiment name only).

Leave the tracking rewards and the base config alone. Quick fixes by symptom:

- Reaches the goal but sloppily -> raise `position_tracking_fine.weight` (or lower its `std`).
- Won't climb / too cautious -> loosen the climbing penalties, lower `upward`, or raise `move_to_goal.weight`.
- Motions getting noisy/unstable again -> lower `entropy_coef` (in [`rsl_rl_ppo_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/position/config/wheeled/unitree_b2w/agents/rsl_rl_ppo_cfg.py)), or restore a mild `is_terminated` penalty.

The reward *functions* never change - only weights, params, and the terrain inside the task file.


### 5.6 Worked example: StaircaseUp teacher

> **Superseded - kept for history.** This walks through the original pose teacher bolted onto the
> velocity package (`RobotLab-Isaac-Velocity-StaircaseUp-Pose-Teacher-Unitree-B2W-v0`). It is replaced
> by the dedicated position package in [Section 5.5](#55-choose-a-reward-tracking-method) and the
> `RobotLab-Isaac-Position-StaircaseUp-Unitree-B2W-v0` task. The weights and terminations below
> (e.g. `position_tracking` weight 10 / `std` 4, added `bad_orientation`) do **not** match the current
> implementation - follow 5.5 to build a position teacher, and read the steps here only as background.

`RobotLab-Isaac-Velocity-StaircaseUp-Pose-Teacher-Unitree-B2W-v0` is just the two choices combined:

1. **Terrain** - the staircase variant from [Section 5.4](#54-plug-in-a-different-terrain).
2. **Reward** - position tracking from [Section 5.5](#55-choose-a-reward-tracking-method).

It is not a third method. Everything below is the 5.4 recipe with the 5.5 position-tracking reward applied. Edit it all in [`staircaseup_pose_teacher_env_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/staircaseup_pose_teacher_env_cfg.py).

#### Step 1 - Swap in the staircase terrain (5.4)

Subclass [`UnitreeB2WRoughEnvCfg`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/rough_env_cfg.py), call `super().__post_init__()`, then replace **only** `self.scene.terrain.terrain_generator`. Leave the robot, actions, observations, and base rewards alone unless a step below changes them. Terrain setup:

| Parameter | Value |
|---|---|
| Terrain type | climb-up inverted pyramid stairs |
| Terrain mix | 50% mesh, 50% heightfield |
| Step height | `0.04 -> 0.30 m` |
| Step width | `0.3 m` |
| Grid | `10 x 20`, `8 m x 8 m` tiles |
| Start level | `max_init_terrain_level = 0` |
| Curriculum | enabled on the new terrain generator |

#### Step 2 - Wire up the task (5.4)

Add the PPO runner entry in [`rsl_rl_ppo_cfg.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/agents/rsl_rl_ppo_cfg.py):

```python
@configclass
class UnitreeB2WStaircaseUpPoseTeacherPPORunnerCfg(UnitreeB2WStaircaseUpTeacherPPORunnerCfg):
    def __post_init__(self):
        super().__post_init__()

        self.experiment_name = "unitree_b2w_staircaseup_pose_teacher"
```

Register the task in [`__init__.py`](../robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/__init__.py):

```python
gym.register(
    id="RobotLab-Isaac-Velocity-StaircaseUp-Pose-Teacher-Unitree-B2W-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": f"{__name__}.staircaseup_pose_teacher_env_cfg:UnitreeB2WStaircaseUpPoseTeacherEnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UnitreeB2WStaircaseUpPoseTeacherPPORunnerCfg",
    },
)
```

#### Step 3 - Switch the command to a pose goal (5.5)

Replace the velocity command with a pose goal:

| Change | Value |
|---|---|
| Replace | `base_velocity` |
| With | `pose_command` / `UniformPose2dCommandCfg` |
| Target range | `pos_x=(-5, 5)`, `pos_y=(-5, 5)`, `heading=(-pi, pi)` |
| Resampling | `(20.0, 20.0)` seconds |
| Heading mode | `simple_heading = False` |

Observation change:

```python
mdp.generated_commands(command_name="pose_command")
```

Apply this to both the policy and critic command observations, so the teacher learns to move toward the goal rather than match an XY velocity.

#### Step 4 - Swap the tracking rewards (5.5)

Disable the inherited velocity rewards:

```python
track_lin_vel_xy_exp
track_ang_vel_z_exp
```

Use these position-tracking rewards instead:

| Reward | Value |
|---|---|
| `position_tracking.weight` | `10.0` |
| `position_tracking.std` | `4.0` |
| `position_tracking_fine.weight` | `0.0` |
| `heading_tracking.weight` | `-0.2` |

Position progress must outweigh the regularization penalties during early learning.

#### Step 5 - Repoint command-gated terms to `pose_command`

Any inherited reward/penalty that checks whether a command exists must now check `pose_command` instead of `base_velocity`, so "has a command" means "still has distance to travel":

```python
stand_still
joint_pos_penalty
feet_height_body
feet_contact_without_cmd
```

#### Step 6 - Lighten the regularization

Position tracking learns slowly at first, so keep penalties light enough that progress rewards dominate:

| Penalty | Value |
|---|---|
| `action_rate_l2.weight` | `-0.001` |
| `joint_pos_penalty.weight` | `-0.15` |
| `joint_torques_l2.weight` | `-5e-6` |
| `joint_power.weight` | `-5e-6` |

#### Step 7 - Use the pose-compatible curriculum

Promotion should depend on moving away from the spawn point, not matching a velocity. Disable the velocity-command curricula and switch the terrain curriculum to the pose variant:

```python
command_levels_lin_vel = None
command_levels_ang_vel = None
```

Use `terrain_levels_pose` instead of `terrain_levels_vel`.

#### Step 8 - Train

Smoke test first:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab

python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-StaircaseUp-Pose-Teacher-Unitree-B2W-v0 \
  --headless \
  --num_envs 64 \
  --max_iterations 5
```

Full run:

```bash
setup_isaaclab
cd /workspace/near-locomotion-quadruped/robot_lab

python scripts/reinforcement_learning/rsl_rl/train.py \
  --task=RobotLab-Isaac-Velocity-StaircaseUp-Pose-Teacher-Unitree-B2W-v0 \
  --headless \
  --num_envs 4096 \
  --max_iterations 8000 \
  --logger wandb \
  --log_project_name b2w-stairsup-teacher
```

Watch these metrics:

| Metric | Expected direction |
|---|---|
| `Episode_Reward/position_tracking` | larger than the main penalties |
| `Train/mean_reward` | should not stay deeply negative |
| `Curriculum/terrain_levels` | should rise above 0 over time |
| `Metrics/pose_command/error_pos_2d` | should trend down |


## 6. Evaluation Matrix

Once more than one policy exists (the staircase teacher from [Section 5.6](#56-worked-example-staircaseup-teacher), a slope teacher, the rough generalist, and eventually the distilled student), they are compared with a **cross-evaluation matrix**: every policy is scored on every terrain. Rows are terrains, columns are policies, each cell is a success rate. The one-command driver and per-cell command live in [Step 2a](#44-step-2a---evaluate-policies-cross-evaluation-matrix); this section documents the code behind them.

### 6.1 What the Matrix Measures

For one (policy, terrain) pair, `--num_envs` robots are spawned across the full difficulty range (rows 0-9) and rolled out for one episode. Two numbers are recorded per cell:

- **Success rate** - fraction of robots that finished the episode **without** triggering the `illegal_contact` (fell) termination.
- **Mean terrain level** - average difficulty row of the robots that survived, i.e. how hard a tile the policy can hold.

Each policy is loaded **actor-only**: a teacher's critic was trained on its own task's privileged observations (whose size differs per terrain - e.g. 247 on rough vs 60 on flat), so loading the full checkpoint into another task would fail on a shape mismatch. Evaluation only runs the actor forward, so the critic is skipped.

### 6.2 New Files

**New file: `scripts/reinforcement_learning/rsl_rl/eval_matrix.py`**

A pure-Python driver (no Isaac Sim imported) that fills the whole matrix by invoking `play_cs.py --eval` once per (terrain, policy) pair, each in its own subprocess. Functions added:

- `newest_checkpoint(experiment_dir)` - newest `model_<N>.pt` under an experiment's newest run.
- `resolve_policy(spec)` - resolve a `.pt` file, an experiment directory, or an experiment name (under `logs/rsl_rl/`) to a concrete checkpoint.
- `discover_policies()` - auto-find every `logs/rsl_rl/unitree_b2w_*` experiment that has a checkpoint (the default columns).
- `main()` - build the (task x policy) grid, run each cell, and report any failures at the end.

**New file: `.../config/wheeled/unitree_b2w/slopeup_teacher_env_cfg.py`**

The slope-climbing teacher - a second specialist column, built exactly like the staircase teacher in [Section 5.6](#56-worked-example-staircaseup-teacher). Adds:

- `SLOPEUP_TEACHER_CFG` - terrain generator, 100% inverted pyramid slope, `slope_range = (0.0, 0.50)` rad.
- `UnitreeB2WSlopeUpTeacherEnvCfg` - the env config class that swaps in that generator.

### 6.3 Changed Files

**Edited: `scripts/reinforcement_learning/rsl_rl/play_cs.py`** - added an opt-in `--eval` mode. Two functions were added - `log_eval_matrix(...)` (writes/accumulates one matrix cell to the CSV, prints it as markdown, and optionally logs a wandb Table) and `run_eval(...)` (rolls out one episode, counts falls, computes the two metrics, calls `log_eval_matrix`). The existing USD-map playback path is unchanged when `--eval` is absent.

New flags:
```diff
+parser.add_argument("--eval", action="store_true", default=False, help="Measure success rate and write a CSV.")
+parser.add_argument("--out_csv", type=str, default="eval_matrix.csv", help="CSV the eval cell is appended to.")
+parser.add_argument("--logger", type=str, default=None, metavar="WANDB_PROJECT", help="wandb project to log to.")
```

Gate the USD-map override so `--eval` runs on the registered task's own terrain, keeping `illegal_contact` ON (it is the failure signal):
<details>
<summary><strong>Click to expand DIFF snippet</strong></summary>

```diff
-    # cs map config
-    env_cfg.scene.terrain = TerrainImporterCfg(... usd_path=args_cli.map ...)
-    ...
-    env_cfg.terminations.illegal_contact = None
-    env_cfg.terminations.terrain_out_of_bounds = None
+    # cs map config (only when a USD map is supplied)
+    if args_cli.map is not None:
+        env_cfg.scene.terrain = TerrainImporterCfg(... usd_path=args_cli.map ...)
+        ...
+        env_cfg.terminations.illegal_contact = None
+        env_cfg.terminations.terrain_out_of_bounds = None
+
+    # eval: spread robots across the full difficulty range, no curriculum promotion
+    if args_cli.eval:
+        env_cfg.curriculum.terrain_levels = None
+        if env_cfg.scene.terrain.terrain_generator is not None:
+            env_cfg.scene.terrain.max_init_terrain_level = None
```

</details>

Load actor-only under `--eval`:
```diff
-    runner.load(resume_path)
+    load_cfg = {"actor": True, "critic": False, "optimizer": False, "iteration": False} if args_cli.eval else None
+    runner.load(resume_path, load_cfg=load_cfg)
```

Run the measurement instead of the interactive loop:
```diff
+    if args_cli.eval:
+        run_eval(env, policy, resume_path,
+                 policy_nn if version.parse(installed_version) < version.parse("4.0.0") else None)
+        env.close()
+        return
```

---

## 7. Skills Trained On

This section tracks which skills the policy has been trained on and which are planned next.

### 7.1 Successfully trained on

**Velocity-tracking locomotion on rough terrain, via a terrain-difficulty curriculum.** The policy is commanded to track body velocities (`±1 m/s` linear, `±1 rad/s` angular) and learns to do so across a mix of terrains that get progressively harder as the policy improves.

**Sub-terrains.** The environment generates a 10-row × 20-column grid of 8 m × 8 m tiles (200 tiles) using `ROUGH_TERRAINS_CFG`. Six terrain types are mixed, each taking a share of the columns, and each type's difficulty parameter scales linearly across the 10 rows (row 0 easiest, row 9 hardest):

<details>
<summary><strong>Click to expand table</strong></summary>

| Terrain Type | Proportion | Difficulty range |
|---|---|---|
| `pyramid_stairs` (ascending) | 20% | step height 5 cm → 23 cm |
| `pyramid_stairs_inv` (descending) | 20% | step height 5 cm → 23 cm |
| `boxes` (raised blocks) | 20% | box height 5 cm → 20 cm |
| `random_rough` (noisy heightfield) | 20% | noise 2 cm → 10 cm |
| `hf_pyramid_slope` (smooth ramp) | 10% | slope 0° → ~22° |
| `hf_pyramid_slope_inv` (concave ramp) | 10% | slope 0° → ~22° |

</details>

**Training method.** RSL-RL PPO with an actor-critic, running **4096 parallel environments**. The actor sees proprioception + velocity commands and outputs joint-position (legs) and wheel-velocity targets; the critic estimates value for GAE and is discarded after training.

**Terrain-difficulty curriculum** (`terrain_levels_vel`). Tiles are arranged in ascending difficulty across rows rather than randomly. The mechanics:

- **Initial placement:** each of the 4096 envs starts at a random level 0–5 (`max_init_terrain_level = 5`), so no robot begins on the hardest half - levels 6–9 are unlocked only by earned progression.
- **Promote / demote (per env, every episode end):** measure straight-line distance travelled from spawn. Walked > 4 m (half a tile) → **promote** one level; walked < 50% of what the commanded velocity required → **demote** one level; in between → no change. This is vectorised across all 4096 envs, no per-robot loop.
- **Respawn:** on the next reset the robot is teleported to a tile at its new level. A robot that clears the hardest row (9) is sent to a *random* level rather than back to 0, so it keeps seeing variety.

Because each env tracks its own level, the population naturally spreads across the difficulty range - most envs sit low early in training, and the distribution shifts upward as the policy improves.

**Velocity-command curriculum - disabled for B2W.** The framework can also start the commanded velocity range at 10% of max and widen it as tracking improves, but for B2W this is turned off (`command_levels_lin_vel = None`, `command_levels_ang_vel = None`). The robot is commanded across the full velocity range from episode one; only *terrain* difficulty is gated.

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

## 8. Challenges Faced

### 8.1 FixStand wheel skid - bug that passed in sim but failed on the real robot

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

## 9. Deriving π in RL

### 9.1 Defining Q-function

$$R_t = r_t + \gamma r_{t+1} + \gamma^2 r_{t+2} + \ldots$$

Total reward, $R_t$, is the discounted sum of all rewards obtained from time $t$. $\gamma$ is the discount factor that basically just means future reward not as "rewarding" as current reward.

$$Q(s_t, a_t) = \mathbb{E}[R_t \mid s_t, a_t]$$

Q-function captures the expected total future reward an agent in state $s$ can receive by executing a certain action, $a$.

Ultimately the agent needs a **policy** $\mathbf{\pi(s)}$, to infer the **best possible action** to take at its state $s$. [i.e. choose the action that maximises future reward]

$$\pi^*(s) = \underset{a}{\arg\max}\, Q(s,a)$$

---

## 10. Proximal Policy Optimisation: PPO (Teacher)

PPO is an on-policy actor-critic policy gradient method. *(called **Proximal** because new policy is kept in the **proximity** of the old one)*

- The **actor** is a stochastic policy $\pi_\theta(a \mid s)$.
- The **critic** $V_\phi(s)$ estimates the state value.

Given that the probability ratio between candidate and data-collecting policies:

$$r_t(\theta) = \frac{\pi_\theta(a_t \mid s_t)}{\pi_{\theta_{old}}(a_t \mid s_t)}$$

### 10.1 Hyperparameters

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
| `clip_param` | `0.2` | `rsl_rl_ppo_cfg.py` | [Clipped Surrogate Objective](#103-clipped-surrogate-objective) ($\varepsilon$); also clips the [Value Loss](#104-value-critic-loss) |
| `value_loss_coef` | `1.0` | `rsl_rl_ppo_cfg.py` | [Value (Critic) Loss](#104-value-critic-loss) - coefficient $c_v$ in the [combined loss](#102-the-combined-ppo-loss) |
| `use_clipped_value_loss` | `True` | `rsl_rl_ppo_cfg.py` | [Value (Critic) Loss](#104-value-critic-loss) - enables the pessimistic clipped critic loss |
| `entropy_coef` | `0.01` | `rsl_rl_ppo_cfg.py` | [Entropy Bonus](#105-entropy-bonus) - coefficient $c_e$ in the [combined loss](#102-the-combined-ppo-loss) |
| `gamma` | `0.99` | `rsl_rl_ppo_cfg.py` | [GAE](#106-generalised-advantage-estimation-gae) - reward discount $\gamma$ |
| `lam` | `0.95` | `rsl_rl_ppo_cfg.py` | [GAE](#106-generalised-advantage-estimation-gae) - baseline-trust factor $\lambda$ |
| `learning_rate` | `1.0e-3` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#107-adaptive-kl-based-learning-rate-schedule) - initial LR |
| `schedule` | `"adaptive"` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#107-adaptive-kl-based-learning-rate-schedule) |
| `desired_kl` | `0.01` | `rsl_rl_ppo_cfg.py` | [Adaptive KL LR schedule](#107-adaptive-kl-based-learning-rate-schedule) - target KL per update |
| `max_grad_norm` | `1.0` | `rsl_rl_ppo_cfg.py` | [Applying the gradients](#109-applying-the-gradients) - gradient-norm clip |

</details>

> **NOTE:** $\gamma$ is the reward discount, while $\lambda$ separately controls how much the value baseline is trusted.

### 10.2 The Combined PPO Loss

**The combined PPO loss** is implemented verbatim in the RSL-RL source as:

```python
loss = surrogate_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy.mean()
```

$$L = L^{\text{policy}} + c_v\, L^V - c_e\, H(\pi_\theta).$$

The coefficient $c_v$ is `value_loss_coef` and $c_e$ is `entropy_coef` (see [Hyperparameters](#101-hyperparameters)).

### 10.3 Clipped Surrogate Objective

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

Here $\varepsilon$ is `clip_param` (see [Hyperparameters](#101-hyperparameters)).

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

### 10.4 Value (Critic) Loss

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

### 10.5 Entropy Bonus

**Entropy Bonus** measures how spread out the policy's action distribution is.

For Gaussian locomotion policy, entropy is a direct function of the action standard deviation:

- **High std**: Policy is exploring a wide range of actions
- **Low std**: Policy is deterministic and committed.

So Entropy bonus encourages exploration by rewarding higher policy entropy $H(\pi_\theta(\cdot \mid s))$.

**Code:** (comes from pytorch)

```python
entropy.mean()
```

### 10.6 Generalised Advantage Estimation (GAE)

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

Here $\gamma$ is `gamma` and $\lambda$ is `lam` (see [Hyperparameters](#101-hyperparameters)).

### 10.7 Adaptive KL-based learning-rate schedule

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

The target `desired_kl` is listed in [Hyperparameters](#101-hyperparameters).

**Essentially**: *It acts as a soft trust region complementing the clip, keeping each update inside a stable policy-change budget regardless of reward scale.*

### 10.8 On-Policy data is used

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

### 10.9 Applying the gradients

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

### 10.10 Privileged Learning

Inside PPO there are two networks:

- The **actor** $\pi_\theta(a \mid s)$: outputs actions. This is what will be deployed.
- The **critic** $V_\phi(s)$: outputs a single number, the estimated value of a state. It exists only to compute advantages $\widehat{A}_t$ (see [GAE](#106-generalised-advantage-estimation-gae)), which tell the actor's gradient which actions were better than expected.

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

## 11. Distillation using DAGGER (Student)

Section 9 trained the **teacher** with PPO, whose privileged critic could see information the real robot will never have. But the **deployed** policy can only use what the onboard sensors provide (proprioception + velocity commands). This section covers how that privileged knowledge is turned into a deployable **student**.

### 11.1 Teacher-Student Distillation Training

In a teacher-student distillation setup:

- The **teacher** (exteroceptive) is the PPO actor from Section 9, trained with RL using privileged terrain and state information.
- The **student** (proprioceptive-only) is trained to imitate the teacher. To compensate for the privileged observations it lacks (height-scan, base linear velocity), the student is given temporal memory - either a recurrent core (LSTM/GRU) or a stacked observation-history - so it can implicitly infer that missing state.
- In this repo, the **default** B2W student (`UnitreeB2WRoughDistillationRunnerCfg`) is a feed-forward MLP `[256, 128, 128]`; the recurrent LSTM student (`UnitreeB2WRoughDistillationRunnerRecurrentCfg`) is an **opt-in variant**, not the default.

This is better than training the proprioceptive policy directly with RL because of a clean division of labour:

- The privileged teacher solves the hard exploration and credit-assignment problem using information the student will never have.
- The student solves the easier problem of mimicking a known-good policy from limited sensing.

### 11.2 DAGGER (Dataset Aggregation)

#### 11.2.1 Behaviour Cloning

The naive alternative to DAgger is **Behaviour Cloning**:

- Collect a dataset of expert state-action pairs, then train the student by supervised learning to reproduce the expert's action at each state.
- **Flaw:** BC fits the student on states drawn from the expert's visitation distribution $\rho_{\pi^*}$. But at deployment, the student is the one driving the system, so it visits its own distribution $\rho_{\widehat{\pi}}$.
- This error compounds because:
  - Suppose the student matches the expert with small per-step error $\epsilon$.
  - The first time it errs, it lands in a state slightly off the expert's distribution, and so on.
  - Errors do not stay independent - they accumulate.
  - Result: BC's worst-case cost grows quadratically in the horizon $T$, because there are $T$ steps where a mistake can happen and a mistake at step $t$ can corrupt all of the roughly $T$ remaining steps.

$$\text{cost}_{BC} = O(T^2 \epsilon)$$

#### 11.2.2 DAgger

**DAgger** fixes this mismatch by training the student on its own state distribution. It iterates the following:

1. Roll out the current student to collect the states it actually visits.
2. Query the teacher for the correct action at each of those visited states.
3. Add these (student-visited state, teacher action) pairs to the dataset and retrain.

Since the student is now trained on exactly the states it will encounter when it drives the system, the train and deployment distributions match. This collapses the compounding and brings the cost down to linear in the horizon:

$$\text{cost}_{DAgger} = O(T\epsilon)$$

**What if there is no current student?** You just let the student run with its randomly initialised weights.

> **TLDR**: the student acts and is allowed to make mistakes, while the teacher only supplies labels.

#### 11.2.3 RSL-RL Implementation: DAgger

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

## 12. Code Walkthrough: train.py

### 12.1 PPO

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

### 12.2 Distillation (MLP Student)

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

### 12.3 Distillation (LSTM Student)

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

> **What actually differs from the MLP run:** `act()`, the rollout loop, and `update()` are the *same generic code*. With the LSTM student the hidden-state machinery inside them (`student.reset(...)`, `detach_hidden_state(...)`, and the `gradient_length`-windowed TBPTT) stops being a no-op and starts carrying/cutting the `h`/`c` state across timesteps. The recurrent config also retunes the algorithm for this: `gradient_length = 24` (widen the TBPTT window to the full rollout so the student integrates a gait cycle of history for velocity inference) and `max_grad_norm = 1.0` (clip BPTT gradients that would otherwise explode through the unrolled LSTM). See [Teacher-Student Distillation Training](#111-teacher-student-distillation-training) and the [RSL-RL DAgger `update()`](#1123-rsl-rl-implementation-dagger) walkthrough for the hidden-state calls.

</details>

---
