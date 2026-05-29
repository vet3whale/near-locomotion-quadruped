# Sim2Real Deployment — Unitree B2W

This document covers deploying the `b2w_ctrl` controller onto the physical
Unitree B2W robot, assuming sim2sim (against `unitree_mujoco`) has already been
validated. If sim2sim is not yet working, see the main `README.md` and complete
that first.

## Prerequisites

- `b2w_ctrl` builds and runs cleanly against `unitree_mujoco` with `robot: "b2w"`.
- Policy file (`policy.onnx`) exists and produces stable behavior in sim2sim
  across the operating envelope you intend to run on hardware (forward,
  backward, lateral, yaw at low speeds).
- Physical B2W is powered on and operational under factory `sport_mode`.
- A wireless remote (for emergency stop) is in hand and tested.
- A Linux machine to run the controller. Two options covered below:
  - **Tethered laptop** (development, recommended for first runs).
  - **Onboard Jetson Orin NX** (production, for untethered operation).

## Architecture Recap

The B2W has two onboard compute units that matter here:

| Address | Name | Role |
|---|---|---|
| `192.168.123.161` | Control Computing Unit | Runs the proprietary `sport_mode` service. Owns the motors when active. |
| `192.168.123.164` | Development Computing Unit (Jetson Orin NX) | User-accessible. Where your `b2w_ctrl` runs when deploying onboard. |

The B2W exposes a private 192.168.123.0/24 ethernet bus internally, shared
between the two computers and the external ethernet port on the chassis. When
your laptop is tethered, it joins this bus. When `b2w_ctrl` runs on the Jetson,
it is already on the bus.

Both the control unit and the Jetson see the same DDS topics. `b2w_ctrl`
publishes `rt/lowcmd` and subscribes to `rt/lowstate` — same topics as in
sim2sim, just real data flowing across them instead of MuJoCo data.

## Key Differences from Sim2Sim

| Aspect | Sim2Sim | Sim2Real |
|---|---|---|
| `dds_domain_id` in `config.yaml` | `1` | `0` |
| `--network` flag | `lo` (loopback) | `eth0` (or the actual NIC name) |
| Counterpart on the DDS bus | `unitree_mujoco` process | The physical robot's motor controllers |
| Pre-launch step | None | Release `sport_mode` on the robot |
| PD gains | Sim values from training | May need tuning for hardware inertia/friction |

The controller binary itself is identical. The only edits before deployment are
to `b2w/config/config.yaml`.

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



---

## Path A — Tethered Laptop (Recommended for First Runs)

### Setup

1. Edit `unitree_rl_lab/deploy/robots/b2w/config/config.yaml`:
```yaml
   dds_domain_id: 0   # was 1 for sim2sim
```
2. Rebuild:
```bash
   cd unitree_rl_lab/deploy/robots/b2w/build
   cmake .. && make -j$(nproc)
```
3. Connect an ethernet cable from your laptop to the robot's external
   ethernet port.
4. Configure your laptop's NIC for the robot's subnet:
```bash
   sudo ip addr add 192.168.123.99/24 dev eth0   # use your actual NIC name
   sudo ip link set eth0 up
```
5. Verify connectivity:
```bash
   ping 192.168.123.161   # the control unit
```
   Should respond. If it doesn't, the cable or IP setup is wrong; do not
   proceed.

### Release `sport_mode`

The factory controller owns `rt/lowcmd` by default. You must release it before
`b2w_ctrl` can send motor commands.

**Via wireless remote (simplest):** Hold `L2 + R2` for about 3 seconds. The
robot should go limp (damping mode). Joints will be soft to the touch; motors
are not actively holding position.

**Via Python SDK (programmatic):**
```python
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import MotionSwitcherClient
ChannelFactoryInitialize(0, "eth0")
msc = MotionSwitcherClient(); msc.Init()
msc.ReleaseMode()
```

### Run the controller

```bash
cd unitree_rl_lab/deploy/robots/b2w
./build/b2w_ctrl --network eth0
```

Expected output:
```bash
--- Unitree Robotics ---
B2W Controller
[INFO] Waiting for connection to robot...
[INFO] Connected to robot.
[INFO] Policy directory: .../unitree_b2w_rough/<date>
```

If it hangs on "Waiting for connection" for more than 30 seconds, see
**Troubleshooting** below.

### Operating sequence

Identical to sim2sim. Keep the controller's terminal focused.

| Key | Action |
|---|---|
| `f` | Passive → FixStand. Legs interpolate to standing pose. |
| `r` | FixStand → Velocity. RL policy engages. |
| `w` / `a` / `s` / `d` / `q` / `e` | Velocity commands. |
| `x` | Emergency stop. Any state → Passive. |

The wireless remote's `L2 + B` also returns the robot to damping mode at any
time and is your fastest physical kill switch.

### Restoring factory control

When done:
1. Stop `b2w_ctrl` (`Ctrl+C`).
2. Either reboot the robot (cleanest), or re-engage `sport_mode` via the
   wireless remote per Unitree's firmware-specific recovery instructions.

The custom policy lives entirely on the laptop. The robot has no persistent
memory of your controller. A power cycle is a complete reset to factory.

---

## Path B — Onboard Jetson Orin NX

Once Path A works reliably, deploy the same controller to the Jetson at
`192.168.123.164` for untethered operation.

### Build on the Jetson

The x86_64 binary built on your workstation will not run on the Jetson's
ARM64. You must rebuild on the Jetson.

```bash
ssh unitree@192.168.123.164    # default user; password per your firmware

# Install build dependencies
sudo apt update
sudo apt install -y libyaml-cpp-dev libboost-all-dev libeigen3-dev \
                    libspdlog-dev libfmt-dev cmake build-essential git

# Build unitree_sdk2
cd ~
git clone https://github.com/unitreerobotics/unitree_sdk2
cd unitree_sdk2
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/.local/unitree_robotics -DBUILD_EXAMPLES=OFF
make install -j$(nproc)
echo 'export CMAKE_PREFIX_PATH=$HOME/.local/unitree_robotics:$CMAKE_PREFIX_PATH' >> ~/.bashrc
source ~/.bashrc

# Get your unitree_rl_lab (clone your fork, or scp from workstation)
cd ~
git clone <your-fork-url>
# OR: scp -r workstation:/path/to/unitree_rl_lab .

# Copy your trained policy onto the Jetson
# (from workstation, in a separate terminal:)
#   scp -r /path/to/logs/rsl_rl/unitree_b2w_rough/<date> \
#          unitree@192.168.123.164:~/unitree_rl_lab/logs/rsl_rl/unitree_b2w_rough/

# Verify policy_dir in b2w/config/config.yaml points to a path that exists
# on the Jetson, not the workstation.

# Build the controller
cd ~/unitree_rl_lab/deploy/robots/b2w
mkdir -p build && cd build
cmake .. && make -j$(nproc)
```

### Find the Jetson's network interface

```bash
ip a
```
Look for an interface with an address in the `192.168.123.0/24` range. Likely
`eth0`. Note its name.

### Run on the Jetson

```bash
# From the SSH session on the Jetson
cd ~/unitree_rl_lab/deploy/robots/b2w
./build/b2w_ctrl --network eth0
```

Release `sport_mode` from the wireless remote as in Path A. Operating sequence
is identical. Keep the SSH session focused for keyboard input. If the SSH
session disconnects, the controller process dies — use `tmux` or `screen` for
persistent sessions.

### Optional: auto-launch on Jetson boot

For demo-ready autonomy, create a systemd unit that waits for a hardware
switch (e.g., a GPIO line, a sentinel file on a USB drive, or a wireless remote
combo) before launching the controller. Untriggered auto-launch is dangerous —
the robot would start running your policy the moment it powers on.

A safer pattern: a systemd `oneshot` triggered manually by SSH:
```bash
sudo systemctl start b2w_ctrl.service
```
This keeps boot benign and makes engagement an explicit operator action.

If you want a starter unit file, ask.

---

## Operating Envelope and Safety

### First runs

For first runs of a new policy on real hardware, regardless of how well
sim2sim performed:
- Operate in a clear area with at least 3m of clearance in all directions.
- Wireless remote in hand throughout. `L2 + B` is your fastest physical stop.
- One person watches the robot, one person at the keyboard. Do not split roles.
- Tap velocity commands. Do not hold. Build up the envelope over multiple
  sessions: ±0.3 m/s linear first, ±0.5 rad/s yaw, then expand.
- If using a hoist for safety, ensure it does not constrain motion in ways the
  policy was not trained for. A loose cargo strap is safer than a taut hoist.

### Sim-to-real gaps to expect

- **Leg PD gains.** Sim values (`stiffness=160`, `damping=5`) may be soft on
  hardware. If standing feels sluggish or wobbly, raise `stiffness` toward
  200–250 in `config/config.yaml`. If motors buzz audibly, lower.
- **Wheel damping.** Sim used `kd=1.0`. Hardware target is `~2.0`. If wheels
  chatter or robot oscillates fore-aft at rest, raise. If response to velocity
  command is sluggish, lower.
- **Continuous drift at zero command.** Likely wheel kd too low, or the policy
  has a small velocity bias from training. Tune kd first; if drift persists,
  retrain with more standing-still data.

Edit gains in `b2w/config/deploy.yaml` (sim/HW gain overrides) and rebuild is
not required for YAML changes — the controller reads them on each `State_RLBase`
construction (i.e., each time you transition into `Velocity`). Some constants in `State_RLBase.cpp` (e.g., `KD_WHEEL`) are
compile-time and require a rebuild.

### Failure modes and immediate responses

| Symptom | Cause | Response |
|---|---|---|
| Robot collapses on `r` | Joint ordering or obs construction error | `x` immediately. Verify against MJCF actuator order. |
| Wheels spin but wrong direction | Sign error in velocity command obs or action | `x`. Check sign of `ang_vel_z` in `keyboard_velocity_commands`. |
| Calves spin instead of wheels | Joint index swap (legs vs. wheels) | `x`. Verify `joint_ids_map` in `deploy.yaml`. |
| Robot stands but drifts forward | Wheel kd too low, or policy bias | Raise `KD_WHEEL` and `damping[12..15]` together. |
| High-frequency leg twitching | Action scale or PD gains mismatched | `x`. Lower `LEG_ACTION_SCALE` or `stiffness`. |
| Audible motor buzzing | PD gains too high | `x`. Lower `stiffness` for legs or `kd` for wheels. |
| Controller hangs at "Waiting for connection" | DDS domain or interface wrong | Verify `dds_domain_id: 0` and correct `--network` arg. |

---

## Troubleshooting

### "Waiting for connection to robot..." never resolves

1. Confirm `dds_domain_id: 0` in `b2w/config/config.yaml`. The real robot uses
   domain 0; only the simulator uses 1.
2. Confirm `--network <name>` matches a real NIC on the running-machine that
   is on the `192.168.123.0/24` subnet. Use `ip a` to verify.
3. Confirm `ping 192.168.123.161` succeeds. If not, the cable, NIC config, or
   robot power state is wrong.
4. Confirm `sport_mode` was released — if the factory controller still owns
   `rt/lowcmd`, your controller may fail to claim the channel cleanly. Try
   `L2 + R2` on the remote again. If using the Python script, confirm it
   reported success.

### Controller connects but FixStand does nothing

- Check terminal focus. Keyboard input only reaches the controller when its
  terminal is focused.
- Check `b2w/config/config.yaml` has `keyboard_transitions:` blocks for the
  `Passive` state and that the `FSMState::keyboard` is initialized in
  `main.cpp` (`std::make_shared<Keyboard>()`, not `nullptr`).

### LowState reports only 12 motor entries

The robot may be running B2 (not B2W) firmware. Confirm firmware version with
Unitree support. The controller assumes 16 motor slots and will misbehave if
only 12 are available.

### Robot moves the wrong joint or collapses on policy start

This is usually a joint-order mismatch between the training environment, the
exported deploy config, and Unitree's `lowcmd.motor_cmd[]` order. Check these
files in order:

1. `unitree_rl_lab/deploy/robots/b2w/config/deploy.yaml`
   - `joint_ids_map` maps policy/action joint index to `lowcmd.motor_cmd[]`
     index. If the wrong physical joint moves, fix the mapping here first.
   - `actions.JointPositionAction.joint_ids` should cover leg joints `0-11`.
   - `actions.JointVelocityAction.joint_ids` should cover wheel joints
     `12-15`.

2. `unitree_rl_lab/deploy/robots/b2w/src/State_RLBase.cpp`
   - The first loop sends action indices `0-11` as leg position targets
     through `motor_cmd[joint_ids_map[i]].q()`.
   - The second loop sends action indices `12-15` as wheel velocity targets
     through `motor_cmd[joint_ids_map[i]].dq()`.
   - If legs and wheels are swapped, or wheels receive position commands,
     verify this split matches the policy's action layout.

3. `robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_b2w/rough_env_cfg.py`
   - `leg_joint_names` defines the training order for the 12 leg actions.
   - `wheel_joint_names` defines the training order for the 4 wheel actions.
   - These lists must match the order expected by `deploy.yaml`.

4. `robot_lab/source/robot_lab/data/Robots/unitree/b2w_description/urdf/b2w_description.urdf`
   - The URDF declaration order may differ from the policy/deploy order.
     For B2W, the policy expects `FR, FL, RR, RL`, while the URDF may list
     joints in a different leg order. Trust named joint lists over raw URDF
     order.

5. `unitree_rl_lab/source/unitree_rl_lab/unitree_rl_lab/utils/export_deploy_cfg.py`
   - This script generates `joint_ids_map` by matching simulated joint names
     to SDK joint names. If you regenerate `deploy.yaml`, inspect the output
     before running on hardware.

For B2W, the intended deploy order is:

```text
0  FR_hip      1  FR_thigh    2  FR_calf
3  FL_hip      4  FL_thigh    5  FL_calf
6  RR_hip      7  RR_thigh    8  RR_calf
9  RL_hip      10 RL_thigh    11 RL_calf
12 FR_wheel    13 FL_wheel    14 RR_wheel    15 RL_wheel
```

If one leg moves when another is commanded, change only `joint_ids_map` first.
If calves spin instead of wheels, check both `joint_ids_map` and the
position/velocity action split in `State_RLBase.cpp`.

### Build fails on Jetson with `find_package(unitree_sdk2)` error

`unitree_sdk2` must be installed (via `make install`), not just cloned. See
the Path B build steps. If installed to a non-default prefix, ensure
`CMAKE_PREFIX_PATH` includes that prefix.

---

## Reverting to Factory Control

A power cycle of the robot is a complete reset. The factory `sport_mode`
service starts on boot and reclaims the motor channel. Nothing your controller
did persists across power cycles — your binary, policy, and tuning all live on
the controlling machine (laptop or Jetson), not on the robot's control unit.

If you copied artifacts onto the Jetson, those persist across robot power
cycles (the Jetson is not wiped) but do not run unless you explicitly invoke
them. To remove the Jetson-side artifacts entirely:
```bash
ssh unitree@192.168.123.164
rm -rf ~/unitree_rl_lab ~/unitree_sdk2 ~/.local/unitree_robotics
```

The robot itself is unaffected by any of this.

---

## References

- `unitree_rl_lab` repository README — base deployment instructions.
- `unitree_sdk2` repository README — SDK build and install.
- `unitree_mujoco` repository README — sim2sim setup.
- `unitree_sdk2_python` repository README — Python SDK for programmatic
  `MotionSwitcherClient` usage.
- Unitree Developer Center (support.unitree.com/home/en/developer) — robot
  firmware, network layout, recovery procedures.
- This repository's `README.md` and `b2w/config/config.yaml` — controller-side
  configuration.
