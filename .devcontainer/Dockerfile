# syntax=docker/dockerfile:1
###############################################################################
# Dev container — Isaac Sim 5.1.0 + ROS 2 Humble
#
# Stack:
#   Base OS  : Ubuntu 24.04 (Noble) — shipped inside nvcr.io/nvidia/isaac-sim:5.1.0
#   ROS      : ROS 2 Humble (targets Ubuntu 22.04/Jammy; compat packages bridge the gap)
#   Isaac Sim: 5.1.0 (Python 3.11, torch cu128, installed at /isaac-sim)
#
# Humble on Noble compatibility shims:
#   - libpython3.10  → deadsnakes PPA (Noble ships 3.12)
#   - libtinyxml2-9  → direct .deb from Ubuntu 22.04/universe (Noble ships v10)
#   - ROS apt source → packages.ros.org with suite=jammy
#
# If you have a prebuilt `isaac-lab-base` image (from IsaacLab's own docker
# tooling) it already has Isaac Lab installed — point BASE_IMAGE at it and set
# ISAACLAB_SRC accordingly, then you can skip the optional IsaacLab clone below.
###############################################################################

ARG BASE_IMAGE=nvcr.io/nvidia/isaac-sim:5.1.0
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# --- Paths (adjust to match your base image) ---------------------------------
# Isaac Sim install root (NGC image: /isaac-sim ; your custom image: /home/isaac_sim)
ARG ISAAC_SIM_PATH=/isaac-sim
# Isaac Lab source root (isaac-lab-base: /workspace/isaaclab ; cloned below otherwise)
ARG ISAACLAB_SRC=/workspace/isaaclab/source
# Where the near-locomotion-quadruped repo is mounted (see devcontainer.json)
ARG REPO_PATH=/workspace/near-locomotion-quadruped
ENV ISAAC_SIM_PATH=${ISAAC_SIM_PATH} \
    ISAACLAB_SRC=${ISAACLAB_SRC} \
    REPO_PATH=${REPO_PATH} \
    ISAAC_PY=${ISAAC_SIM_PATH}/kit/python/bin/python3.11

# =============================================================================
# Step 3 (prereq) — ROS 2 Humble + CycloneDDS rmw
#   This is the main OS delta vs. the 24.04/Jazzy setup.
# =============================================================================
USER root
ENV ROS_DISTRO=humble
# ROS Humble is built for Ubuntu 22.04 but Isaac Sim 5.x uses Ubuntu 24.04.
# Pre-install the Ubuntu 22.04-only libraries that ROS Humble .deb deps require:
#   - libpython3.10     → deadsnakes PPA (Noble ships 3.12)
#   - libtinyxml2-9     → Ubuntu 22.04 universe (Noble ships v10)
#   - libyaml-cpp0.7    → Ubuntu 22.04 main   (Noble ships 0.8)
#   - libfmt8           → Ubuntu 22.04 universe (Noble ships 9+); needed by libspdlog1
#   - libspdlog1        → Ubuntu 22.04 universe; Provides: libspdlog1-fmt8 (virtual pkg ROS needs)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 lsb-release software-properties-common locales git ca-certificates equivs \
        python3-venv \
    && locale-gen en_US en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends libpython3.10 \
    # Ubuntu 22.04-only compat packages needed by ROS Humble
    && curl -fsSL -o /tmp/libtinyxml2-9.deb \
        "http://mirrors.kernel.org/ubuntu/pool/universe/t/tinyxml2/libtinyxml2-9_9.0.0+dfsg-3_amd64.deb" \
    && curl -fsSL -o /tmp/libyaml-cpp0.7.deb \
        "http://mirrors.kernel.org/ubuntu/pool/main/y/yaml-cpp/libyaml-cpp0.7_0.7.0+dfsg-8build1_amd64.deb" \
    && curl -fsSL -o /tmp/libfmt8.deb \
        "http://mirrors.kernel.org/ubuntu/pool/universe/f/fmtlib/libfmt8_8.1.1+ds1-2_amd64.deb" \
    && dpkg -i /tmp/libtinyxml2-9.deb /tmp/libyaml-cpp0.7.deb /tmp/libfmt8.deb \
    && rm /tmp/libtinyxml2-9.deb /tmp/libyaml-cpp0.7.deb /tmp/libfmt8.deb \
    # Create stub libspdlog1 package that satisfies the libspdlog1-fmt8 virtual dep.
    # Noble's libspdlog1.12 declares Breaks: libspdlog1 (< 1:1.10.0+ds-0.3), so we set
    # the stub version to exactly 1:1.10.0+ds-0.3 — equal is NOT less-than, no conflict.
    && printf 'Section: libs\nPriority: optional\nStandards-Version: 3.9.2\n\nPackage: libspdlog1\nVersion: 1:1.10.0+ds-0.3\nProvides: libspdlog1-fmt8\nArchitecture: amd64\nDescription: Stub satisfying libspdlog1-fmt8 virtual dep for ROS Humble on Noble\n' \
        > /tmp/libspdlog1-stub.ctl \
    && cd /tmp && equivs-build libspdlog1-stub.ctl \
    && dpkg -i /tmp/libspdlog1_1.10.0+ds-0.3_amd64.deb \
    && rm -f /tmp/libspdlog1-stub.ctl /tmp/libspdlog1_*.deb \
    # Create libspdlog.so.1 compat symlink so ROS Humble ELFs find the runtime.
    # Noble ships libspdlog.so.1.12.0; point .so.1 at it for ABI-stable logging calls.
    && SPDLOG_REAL=$(find /usr/lib/x86_64-linux-gnu -maxdepth 1 -name 'libspdlog.so.*.*' ! -type l 2>/dev/null | sort -V | tail -1) \
    && if [ -n "${SPDLOG_REAL}" ]; then ln -sf "${SPDLOG_REAL}" /usr/lib/x86_64-linux-gnu/libspdlog.so.1; fi \
    # ROS 2 Humble apt repo (jammy suite — Humble has no native Noble packages)
    && curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" \
        > /etc/apt/sources.list.d/ros2.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        ros-humble-ros-base \
        ros-humble-rmw-cyclonedds-cpp \
        python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Step 2 — system-wide `python` -> Isaac Sim's Python 3.11
#   (Ubuntu only ships python3; many robot_lab scripts call bare `python`.)
# =============================================================================
RUN ln -sf ${ISAAC_PY} /usr/local/bin/python

# =============================================================================
# Step 4 — Isaac Lab / RSL-RL deps into Isaac Sim's Python 3.11 (--no-deps)
#   --no-deps avoids pulling a second multi-GB torch; the bundled
#   torch 2.7.0+cu128 already satisfies rsl-rl-lib's torch>=2.6.0.
# =============================================================================
RUN ${ISAAC_PY} -m pip install --no-deps \
        flatdict h5py numpy \
        rsl-rl-lib \
        tensordict pyvers cloudpickle importlib_metadata orjson \
        onnx onnxscript onnx_ir protobuf \
        GitPython gitdb smmap \
        torchvision pillow \
        packaging typing_extensions zipp \
 && ${ISAAC_PY} -m pip install cusrl

# =============================================================================
# (Optional) clone Isaac Lab if your BASE_IMAGE doesn't already include it.
#   Skip this if you used an isaac-lab-base image. Uncomment to enable.
# =============================================================================
# RUN apt-get update && apt-get install -y --no-install-recommends \
#         libegl-dev libgl-dev libgles-dev \
#         libegl-mesa0 libgl1-mesa-dri libgbm1 \
#     && rm -rf /var/lib/apt/lists/*

# RUN git clone https://github.com/isaac-sim/IsaacLab.git /workspace/isaaclab \
#  && ln -sf ${ISAAC_SIM_PATH} /workspace/isaaclab/_isaac_sim \
#  && cd /workspace/isaaclab && TERM=xterm ./isaaclab.sh -i

# =============================================================================
# Step 5 — standalone PyTorch venv (system Python 3.10 on 22.04, CUDA 12.8)
#   For non-Isaac tooling only. Heavy (~GBs); comment out to speed up builds.
# =============================================================================
RUN python3 -m venv /opt/torch-env \
 && /opt/torch-env/bin/pip install --upgrade pip \
 && /opt/torch-env/bin/pip install --pre torch torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/nightly/cu128

# =============================================================================
# Step 3 — ~/.bashrc additions (ROS block + setup_isaaclab)
#   Written to isaac-sim's bashrc (~/.bashrc = /isaac-sim/.bashrc).
# =============================================================================
RUN cat >> /isaac-sim/.bashrc <<'BASHRC'

# ── ROS2 ──────────────────────────────────────────────────────────────────
# Clear PYTHONPATH before sourcing ROS2 so its Python 3.10 overlay starts clean.
unset PYTHONPATH
if [ -f "/opt/ros/${ROS_DISTRO:-humble}/setup.bash" ]; then
    source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"
fi
if [ -f "/workspace/install/setup.bash" ]; then
    source /workspace/install/setup.bash
fi
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# ── Isaac Lab ───────────────────────────────────────────────────────────────
# Call once per terminal before running any Isaac Lab script.
setup_isaaclab() {
    unset PYTHONPATH

    # Isaac Sim core env vars (required by AppLauncher)
    export ISAAC_PATH="${ISAAC_SIM_PATH}"
    export CARB_APP_PATH="${ISAAC_SIM_PATH}/kit"
    export EXP_PATH="${ISAAC_SIM_PATH}/apps"

    # Isaac Sim core packages (isaacsim, omni, carb, …)
    source "${ISAAC_SIM_PATH}/setup_python_env.sh"

    # Isaac Lab source packages
    local _il_src="${ISAACLAB_SRC}"
    for _p in isaaclab isaaclab_assets isaaclab_contrib isaaclab_mimic isaaclab_rl isaaclab_tasks; do
        export PYTHONPATH="${PYTHONPATH}:${_il_src}/${_p}"
    done

    # near-locomotion-quadruped tasks / assets
    export PYTHONPATH="${PYTHONPATH}:${REPO_PATH}/robot_lab/source/robot_lab"
    export PYTHONPATH="${PYTHONPATH}:${REPO_PATH}/unitree_rl_lab/source/unitree_rl_lab"

    # Put Isaac Sim Python 3.11 ahead of system Python 3.10
    export PATH="${ISAAC_SIM_PATH}/kit/python/bin:$PATH"
    alias python='python3.11'
    alias python3='python3.11'

    echo "[setup_isaaclab] Ready — $(python3.11 --version)"
}

# ── Sim2Sim ──────────────────────────────────────────────────────────────────
# Call once per terminal before running unitree_mujoco or b2w_ctrl.
sim2sim_env() {
    unset ROS_DISTRO AMENT_PREFIX_PATH CMAKE_PREFIX_PATH LD_LIBRARY_PATH
    export LD_LIBRARY_PATH=/usr/local/lib:/usr/lib/x86_64-linux-gnu
    export CYCLONEDDS_URI='<CycloneDDS><Domain><Iceoryx><Enable>false</Enable></Iceoryx></Domain></CycloneDDS>'
}
BASHRC

# Isaac Sim EULA / telemetry acknowledgements (also set in devcontainer.json).
ENV ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y

# Give isaac-sim ownership of the workspace mount-point so it can write there.
# sudo is also installed so postCreateCommand can re-assert ownership after the
# devcontainer runtime mounts the bind-mount (which can recreate /workspace as root).
RUN apt-get update && apt-get install -y --no-install-recommends sudo \
    && rm -rf /var/lib/apt/lists/* \
    && echo "isaac-sim ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/isaac-sim \
    && chmod 0440 /etc/sudoers.d/isaac-sim \
    && mkdir -p /workspace/near-locomotion-quadruped \
    && chown -R isaac-sim:isaac-sim /workspace \
    && mkdir -p /isaac-sim/kit/cache \
    && chown -R isaac-sim:isaac-sim /isaac-sim/kit/cache

USER isaac-sim
WORKDIR ${REPO_PATH}
