# B2W MuJoCo Sim2Sim Validation Guide

This document records every change made to enable sim2sim validation of the Unitree B2W
(wheeled B2) RL policy in `unitree_mujoco`, and provides a complete runbook for running
the loop with a USB keyboard instead of a gamepad.

---

## Table of Contents

1. [Overview](#overview)
2. [Repository Layout](#repository-layout)
3. [Code Changes Made](#code-changes-made)
   - [Shared headers (unitree_rl_lab)](#shared-headers-unitree_rl_lab)
   - [B2W-specific files](#b2w-specific-files)
4. [Prerequisite Installation](#prerequisite-installation)
5. [Pre-Flight Configuration](#pre-flight-configuration)
6. [Terrain Generation](#terrain-generation)
7. [Sim2Sim Runbook](#sim2sim-runbook)
8. [Key Bindings Reference](#key-bindings-reference)
9. [What to Watch For](#what-to-watch-for)
10. [Failure Modes and Diagnostics](#failure-modes-and-diagnostics)
11. [Switching to Gamepad](#switching-to-gamepad)

---

## Overview

The B2W has 16 DOF: 12 leg joints (FR/FL/RR/RL × hip/thigh/calf) controlled by position PD,
and 4 wheel joints (FR/FL/RR/RL foot) controlled by velocity (kp=0, kd-only). The RL policy
was trained in IsaacLab (`robot_lab/`) and exported to ONNX. Sim2sim runs the C++ controller
(`unitree_rl_lab/deploy/robots/b2w/`) against the MuJoCo simulator (`unitree_mujoco/`) over
DDS on loopback, without a physical robot.

**Training policy location** (auto-selected by `parser_policy_dir`):
```
robot_lab/logs/rsl_rl/unitree_b2w_rough/<latest-timestamp>/
  exported/policy.onnx ← copy manually from training host; not committed
```

**Shared deploy config** (loaded by the controller at startup):
```
unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml  ← observation/action config (editable)
```

`parser_policy_dir` is defined in
`unitree_rl_lab/deploy/include/param.h` and called from
`unitree_rl_lab/deploy/robots/b2w/src/State_RLBase.cpp`. It receives
the `policy_dir` path from `b2w/config/config.yaml` and resolves it as
follows:

1. If the path is relative, it is resolved against the controller binary's
   directory (`unitree_rl_lab/deploy/robots/b2w/build/`).
2. If an `exported/` folder exists directly at that path, it is used as-is.
3. Otherwise the path is treated as a parent directory — all subdirectories
   are sorted alphabetically and the last one that contains an `exported/`
   folder is selected (i.e. the most recent timestamp run).

This means `policy_dir` in `config.yaml` only ever needs to point at the
`unitree_b2w_rough/` log root; the controller always picks up the newest
exported policy automatically.

---

## Repository Layout

```
near-locomotion-quadruped/
├── robot_lab/                          ← IsaacLab training (do NOT edit source)
│   └── logs/rsl_rl/unitree_b2w_rough/ ← training output (logs/ is safe to edit)
│       └── <timestamp>/
│           └── exported/policy.onnx   ← place manually
├── unitree_mujoco/                     ← MuJoCo DDS bridge (submodule)
│   └── simulate/
│       ├── config.yaml                 ← set robot: "b2w"
│       └── unitree_robots/b2w/         ← MJCF model must exist here
└── unitree_rl_lab/deploy/
    ├── include/
    │   ├── FSM/FSMState.h              ← MODIFIED: keyboard_transitions support
    │   └── isaaclab/envs/mdp/observations/observations.h
    │                                   ← MODIFIED: joint_pos_rel_without_wheel
    └── robots/b2w/                     ← NEW: B2W controller (forked from b2/)
        ├── CMakeLists.txt
        ├── main.cpp
        ├── config/
        │   ├── config.yaml
        │   └── deploy.yaml             ← shared obs/action config (all policies)
        ├── src/State_RLBase.cpp
        └── README.md
```

---

## Code Changes Made

### Shared headers (unitree_rl_lab)

These files are shared across all robots. Changes are backward-compatible and gated so
existing robots (b2, go2, h1, g1_29dof) are unaffected.

#### `deploy/include/FSM/FSMState.h` — keyboard FSM transitions

Added a `keyboard_transitions` parsing block immediately after the existing `transitions`
block and before `// register for all states`. When `FSMState::keyboard` is `nullptr`
(which it is for robots that don't initialize it in `main.cpp`), the block is skipped.

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
Transitions are edge-triggered (`on_pressed`, not held), so a brief keypress advances the FSM.

#### `deploy/include/isaaclab/envs/mdp/observations/observations.h` — wheel-masked joint positions

The B2W policy was trained with `joint_pos_rel_without_wheel`: a 16-element vector of
`q - q_default` where the four wheel slots [12–15] are forced to 0.0. (Wheel position is
undefined for continuously-spinning joints, so feeding the raw value there is wrong.)

Added a generic C++ equivalent between `joint_pos_rel` and `joint_vel_rel`:

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

---

### B2W-specific files

#### `deploy/robots/b2w/config/config.yaml`

Key changes from the b2 template:
- `dds_domain_id: 1` — simulator domain (change to 0 for real robot)
- 16-entry arrays for `mode`, `kp`, `kd`, `qs` (12 leg + 4 wheel slots)
- Wheel kp = 0 in FixStand (velocity-controlled)
- `keyboard_transitions` blocks for all three states
- `policy_dir` points to `robot_lab/logs/rsl_rl/unitree_b2w_rough`

```yaml
dds_domain_id: 1  # 1 = simulator; 0 = real robot

FSM:
  Passive:
    keyboard_transitions:
      FixStand: "f"
  FixStand:
    keyboard_transitions:
      Passive:  "x"
      Velocity: "r"
  Velocity:
    keyboard_transitions:
      Passive: "x"
    policy_dir: ../../../../robot_lab/logs/rsl_rl/unitree_b2w_rough
```

#### `deploy/robots/b2w/main.cpp`

- Reads `dds_domain_id` from config rather than hardcoding 0
- Initializes `FSMState::keyboard = std::make_shared<Keyboard>()` (enables keyboard support)

```cpp
unitree::robot::ChannelFactory::Instance()->Init(
    param::config["dds_domain_id"].as<int>(), vm["network"].as<std::string>());
```

#### `deploy/robots/b2w/src/State_RLBase.cpp`

Two sections:

**1. Namespace `isaaclab` — `keyboard_velocity_commands` observation**

Maps key strings to `[lin_vel_x, lin_vel_y, ang_vel_z]` vectors. Registered via
`REGISTER_OBSERVATION` so the observation manager can call it by name. Enabled by using
`keyboard_velocity_commands` (not `velocity_commands`) as the key in `deploy.yaml`.

```
WASD ring:  w=forward, s=backward, a=left, d=right, q=yaw-CCW, e=yaw-CW
Arrow keys: up=forward, down=backward, left=yaw-CCW, right=yaw-CW
Numpad:     8=forward, 2=backward, 4=left, 6=right, 7=yaw-CCW, 9=yaw-CW
No key:     [0, 0, 0] (stop)
```

**2. Hybrid control loop in `State_RLBase::run()`**

```cpp
// Leg joints [0, 12): position PD (processed_actions returns default_pos + scale*action)
for(int i(0); i < 12; i++)
    lowcmd->msg_.motor_cmd()[env->robot->data.joint_ids_map[i]].q() = action[i];

// Wheel joints [12, 16): velocity control (kp=0, kd=KD_WHEEL)
// processed_actions() already applies scale=5.0; do NOT multiply again
for(int i(12); i < 16; i++) {
    auto& mc = lowcmd->msg_.motor_cmd()[env->robot->data.joint_ids_map[i]];
    mc.q()   = 0.0f;
    mc.dq()  = action[i];
    mc.kp()  = 0.0f;
    mc.kd()  = KD_WHEEL;  // = 1.0f (must match deploy.yaml damping[12..15])
    mc.tau() = 0.0f;
}
```

#### `deploy/robots/b2w/config/deploy.yaml`

Shared across all B2W policies — no longer stored per-policy run. The controller loads
it from `b2w/config/deploy.yaml` on every startup.

- `velocity_commands` commented out; `keyboard_velocity_commands` active
- `joint_pos_rel` replaced with `joint_pos_rel_without_wheel` (wheel_joint_ids: [12,13,14,15])
- `joint_ids_map: [0..15]` — identity mapping (MJCF actuator order matches training order)
- Wheel `stiffness[12..15] = 0.0`, `damping[12..15] = 1.0`

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
> the observation vector fed to ONNX is empty (0 elements) → ONNX reads past the buffer
> → stack corruption → segfault on the first policy step (pressing `r`).
> All six terms in `deploy.yaml` already have `history_length: 1` — do not change them to 0.

---

## Prerequisite Installation

These steps are required once on the host machine before the first build.

### 1. System packages

```bash
sudo apt update
sudo apt install -y libyaml-cpp-dev libspdlog-dev libboost-all-dev
```

> **`libglfw3-dev` may not be in the apt repos** (observed on Ubuntu 24.04 with restricted mirrors).
> If `sudo apt install -y libglfw3-dev` fails with "Unable to locate package", build GLFW from source:
> ```bash
> sudo apt install -y cmake xorg-dev
> git clone https://github.com/glfw/glfw.git /tmp/glfw
> cmake -S /tmp/glfw -B /tmp/glfw/build \
>   -DCMAKE_BUILD_TYPE=Release \
>   -DCMAKE_INSTALL_PREFIX=/usr/local \
>   -DBUILD_SHARED_LIBS=ON \
>   -DGLFW_BUILD_DOCS=OFF -DGLFW_BUILD_TESTS=OFF -DGLFW_BUILD_EXAMPLES=OFF
> sudo cmake --build /tmp/glfw/build --target install -j$(nproc)
> ```

### 2. unitree_sdk2

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

### 3. MuJoCo 3.3.6

```bash
mkdir -p ~/.mujoco && cd ~/.mujoco
wget https://github.com/google-deepmind/mujoco/releases/download/3.3.6/mujoco-3.3.6-linux-x86_64.tar.gz
tar -xzf mujoco-3.3.6-linux-x86_64.tar.gz

# Symlink into the simulate/ source tree (CMakeLists.txt expects simulate/mujoco/)
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate
ln -s ~/.mujoco/mujoco-3.3.6 mujoco
```

### 4. Build unitree_mujoco

```bash
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

Binary: `unitree_mujoco/simulate/build/unitree_mujoco`

### 5. Build the B2W controller

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
cmake ..
make -j$(nproc)
```

Binary: `unitree_rl_lab/deploy/robots/b2w/build/b2w_ctrl`

---

## Pre-Flight Configuration

### unitree_mujoco/simulate/config.yaml

```yaml
robot: "b2w"          # ← change from "go2"
domain_id: 1          # must match dds_domain_id in b2w/config/config.yaml
interface: "lo"       # loopback for sim2sim
use_joystick: 0       # 0 = no USB gamepad required (keyboard mode)
```

### MJCF model

Confirm `unitree_mujoco/simulate/unitree_robots/b2w/` exists and contains `b2w.xml`.
If absent, obtain from the Unitree MuJoCo model pack.

**Verified actuator order in b2w.xml** (matches training order — no permutation needed):
```
[0]  FR_hip   [1]  FR_thigh  [2]  FR_calf
[3]  FL_hip   [4]  FL_thigh  [5]  FL_calf
[6]  RR_hip   [7]  RR_thigh  [8]  RR_calf
[9]  RL_hip   [10] RL_thigh  [11] RL_calf
[12] FR_foot  [13] FL_foot   [14] RR_foot  [15] RL_foot
```

### ONNX policy file

Copy the policy from the training host manually — it is not committed to git:

```bash
# On training host:
scp robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/exported/policy.onnx \
    <deploy-host>:/workspace/near-locomotion-quadruped/robot_lab/logs/rsl_rl/unitree_b2w_rough/<timestamp>/exported/
```

---

## Terrain Generation

The simulator ships with a flat ground scene (`scene.xml`) for each robot. Use the terrain
generator tool to produce a `scene_terrain.xml` that adds obstacles, rough ground, or Perlin
heightfields. Switching between them is a one-line change in `config.yaml`.

### Prerequisites (once)

```bash
pip3 install noise --break-system-packages   # numpy and opencv are already installed
```

> The system Python on Ubuntu 24.04 is externally-managed; `--break-system-packages` is
> safe for the small, pure-Python `noise` package.

### Generate terrain

The generator reads a template `scene.xml` and writes a new `scene_terrain.xml` with added
geometry. **Use the robot's own `scene.xml` as input**, not the template in `terrain_tool/`
(which references `go2.xml`):

```bash
cd /workspace/near-locomotion-quadruped/unitree_mujoco/terrain_tool

# Point the generator at the b2w template and run
python3 - <<'EOF'
import terrain_generator as tg_module, importlib, sys
tg_module.ROBOT = "b2w"
tg_module.INPUT_SCENE_PATH  = "../unitree_robots/b2w/scene.xml"
tg_module.OUTPUT_SCENE_PATH = "../unitree_robots/b2w/scene_terrain.xml"
tg = tg_module.TerrainGenerator()
# Perlin heightfield — smooth undulating terrain, good for rough-terrain policy testing
tg.AddPerlinHeighField(position=[0.0, 0.0, 0.0], size=[10.0, 10.0], height_scale=0.15)
# Rough ground — random cube field
tg.AddRoughGround(init_pos=[-5.0, -5.0, 0.0], nums=[20, 20],
                  box_size=[0.5, 0.5, 0.15], box_euler_rand=[0.1, 0.1, 0.1])
tg.Save()
print("Written: ../unitree_robots/b2w/scene_terrain.xml")
EOF
```

Alternatively, edit `terrain_generator.py` directly: change `ROBOT = "go2"` to `ROBOT = "b2w"`
and change `INPUT_SCENE_PATH = "./scene.xml"` to
`INPUT_SCENE_PATH = "../unitree_robots/b2w/scene.xml"`, then run `python3 terrain_generator.py`.

> **Why the input path matters:** The template `terrain_tool/scene.xml` includes `go2.xml`,
> so the generated file would reference the wrong robot model and MuJoCo would fail with
> `XML Error: Error opening file '.../b2w/go2.xml'`. Always use the robot-specific `scene.xml`.

### Switch between flat and terrain scenes

In `unitree_mujoco/simulate/config.yaml`:
```yaml
# Flat ground (default):
robot_scene: "scene.xml"

# Terrain:
robot_scene: "scene_terrain.xml"
```

Then restart `./unitree_mujoco`.

### Available terrain functions

| Function | Description | Key parameters |
|----------|-------------|----------------|
| `AddRoughGround` | Random cube field | `nums=[N,N]` grid, `box_size`, `box_euler_rand` for tilt |
| `AddPerlinHeighField` | Smooth undulating surface via Perlin noise | `size`, `height_scale`, `smoothness` |
| `AddStairs` | Ascending staircase | `width`, `height`, `stair_nums` |
| `AddSuspendStairs` | Floating stairs with gaps | `gap` |
| `AddBox` | Single box obstacle | `position`, `euler`, `size` |
| `AddGeometry` | sphere, cylinder, capsule, etc. | `geo_type` |
| `AddHeighFieldFromImage` | Terrain from a grayscale image | `input_img`, `height_scale` |

---

## Sim2Sim Runbook

Open **two terminals** in the same working directory.

### Environment setup (required in every terminal before running)

If this machine has ROS installed, its `LD_LIBRARY_PATH` and `CMAKE_PREFIX_PATH` conflict with
the Unitree SDK and CycloneDDS, and Iceoryx shared memory causes a `free(): invalid pointer`
crash on startup. Call the `sim2sim_env` shell function (defined in `~/.bashrc`) to strip ROS
variables and disable Iceoryx:

```bash
sim2sim_env
```

Alternatively, source the equivalent one-shot script:

```bash
source /workspace/near-locomotion-quadruped/scripts/sim2sim_env.sh
```

Or set the variables manually:

```bash
unset ROS_DISTRO AMENT_PREFIX_PATH CMAKE_PREFIX_PATH LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/local/lib:/usr/lib/x86_64-linux-gnu
export CYCLONEDDS_URI='<CycloneDDS><Domain><Iceoryx><Enable>false</Enable></Iceoryx></Domain></CycloneDDS>'
```

> **Why:** ROS 2 sets `LD_LIBRARY_PATH` to its own lib directories, which causes the dynamic
> linker to pick up ROS-bundled versions of CycloneDDS/FastDDS instead of the SDK's version.
> The Iceoryx transport in CycloneDDS also requires shared memory that isn't present in a
> headless/container environment, triggering the crash. Setting `CYCLONEDDS_URI` forces
> CycloneDDS to fall back to UDP-only transport.

### Terminal 1 — MuJoCo simulator

```bash
sim2sim_env
cd /workspace/near-locomotion-quadruped/unitree_mujoco/simulate/build
./unitree_mujoco
```

The MuJoCo viewer opens. The robot loads in its default pose. DDS topics start publishing
on `lo` interface, domain 1.

### Terminal 2 — B2W controller

```bash
sim2sim_env
cd /workspace/near-locomotion-quadruped/unitree_rl_lab/deploy/robots/b2w/build
./b2w_ctrl --network lo
```

Expected output:
```
 --- Unitree Robotics ---
     B2W Controller
[info] Waiting for connection to robot...
[info] Connected to robot.
[info] Initializing State_Passive ...
[info] Initializing State_FixStand ...
[info] Initializing State_Velocity ...
Press [L2 + A] to enter FixStand mode.
And then press [Start] to start controlling the robot.
```

Keep Terminal 2 focused (keyboard reads from stdin of this process).

### Operating Sequence

| Step | Action | Key | Expected |
|------|--------|-----|----------|
| 1 | Start in Passive | — | Robot limp, gravity settle |
| 2 | Enter FixStand | `f` | Robot stands up over ~3 s |
| 3 | Enter Velocity | `r` | Policy activates, legs begin cycling |
| 4 | Drive forward | `w` | Robot walks/rolls forward |
| 5 | Turn left | `q` | Robot yaws counter-clockwise |
| 6 | Stop | (release / other key) | Robot holds position |
| 7 | Return to Passive | `x` | Robot lowers and goes limp |

---

## Key Bindings Reference

### FSM transitions (edge-triggered, one keypress)

| Key | From | To |
|-----|------|----|
| `f` | Passive | FixStand |
| `r` | FixStand | Velocity |
| `x` | FixStand or Velocity | Passive |

### Velocity commands (held — active while key is down)

| Key | lin_vel_x | lin_vel_y | ang_vel_z | Description |
|-----|-----------|-----------|-----------|-------------|
| `w` / `↑` / numpad `8` | +1.0 | 0 | 0 | Forward |
| `s` / `↓` / numpad `2` | −1.0 | 0 | 0 | Backward |
| `a` / numpad `4` | 0 | +1.0 | 0 | Strafe left |
| `d` / numpad `6` | 0 | −1.0 | 0 | Strafe right |
| `q` / `←` / numpad `7` | 0 | 0 | +1.0 | Yaw CCW |
| `e` / `→` / numpad `9` | 0 | 0 | −1.0 | Yaw CW |
| Any other key | 0 | 0 | 0 | Stop |

Values are ±1.0; actual velocity is set by `commands.base_velocity.ranges` in `deploy.yaml`
(default ±1.0 m/s and ±1.0 rad/s). The `keyboard_velocity_commands` scale in `deploy.yaml`
is 1.0 — no additional scaling is applied.

**Note:** The Keyboard class reads raw terminal input (stdin). Arrow keys and numpad digits
work only when the **Terminal 2 window is focused**. NumLock must be on for numpad.

---

## What to Watch For

- **Robot stands cleanly in FixStand**: legs reach `[0.0, 0.8, −1.5]` rad and hold. Wheels idle at 0 rad/s.
- **Smooth policy rollout**: in Velocity mode the legs should show a consistent gait pattern; wheels should spin proportionally to the commanded velocity.
- **Observation dimension**: the policy expects 57 inputs. If you see an ONNX shape error at startup, count the active observation terms in `deploy.yaml`.
- **DDS latency**: `lowstate->isTimeout()` triggers a fallback to Passive if no LowState message arrives within the timeout. If the controller immediately reverts to Passive, the simulator domain/interface may not match.
- **Wheel direction**: positive `dq` should drive the robot forward. If the robot moves backward under `w`, negate the wheel action scale or swap FR/RL sign convention.

---

## Failure Modes and Diagnostics

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Controller reverts to Passive immediately | DDS domain mismatch | Confirm `dds_domain_id: 1` in `b2w/config/config.yaml` AND `domain_id: 1` in `simulate/config.yaml` |
| "The other process is using the lowcmd channel" | Stale controller process | `pkill b2w_controller` |
| ONNX shape error at load | Wrong policy file or extra/missing obs term | Check obs count in deploy.yaml (should be 57) |
| Robot tilts and falls immediately | bad_orientation safety check fires | Verify projected_gravity and imu are publishing correctly |
| Keyboard input not responding | Terminal 2 not focused, or stdin not a tty | SSH with `-t` flag; ensure no pipe/redirect on the controller process |
| Numpad keys not recognized | NumLock off | Press NumLock; digits 0–9 must be in numpad mode |
| Segfault (SIGSEGV) immediately on pressing `r` | `history_length: 0` in deploy.yaml causes empty observation buffers → ONNX reads past a 0-byte buffer | Set all observation `history_length` values to `1` in deploy.yaml |
| Wheels spin but legs don't move | Position PD gains not applied | Check `stiffness[0..11]` are non-zero in deploy.yaml (should be 160.0) |
| Legs move but wheels don't | Wheel kd=0 | Confirm `damping[12..15]` > 0 in deploy.yaml and `KD_WHEEL > 0` in State_RLBase.cpp |
| cmake: cannot find unitree_sdk2 | SDK not installed | Follow [Prerequisite Installation §2](#2-unitree_sdk2) |
| cmake: mujoco not found | Symlink missing | Follow [Prerequisite Installation §3](#3-mujoco-336) |
| Simulator prints go2/b2 joints, not b2w | `config.yaml` still has `robot: "go2"` | Change to `robot: "b2w"` and save |
| `corrupted size vs. prev_size` / core dump on startup | GLFW cannot open a display window (headless SSH session) | Run `Xvfb :99 -screen 0 1280x720x24 &` then `DISPLAY=:99 ./unitree_mujoco`, or enable X11 forwarding (`ssh -X`) |

---

## Switching to Gamepad

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

