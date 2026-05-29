# Rough Terrain Curriculum Training — Unitree B2W

## Training Command

```bash
cd /workspace/near-locomotion-quadruped/robot_lab
python scripts/reinforcement_learning/rsl_rl/train.py --task=RobotLab-Isaac-Velocity-Rough-Unitree-B2W-v0
```

---

## Sub-Terrains

The environment generates a grid of terrain tiles using `ROUGH_TERRAINS_CFG` (defined in `isaaclab/terrains/config/rough.py`). Six terrain types are mixed together, each assigned a proportion of the total columns:

| Terrain Type | Proportion | Difficulty Parameter | Description |
|---|---|---|---|
| `pyramid_stairs` | 20% | step height: 5 cm → 23 cm | Ascending pyramid of steps — robot must climb up and over |
| `pyramid_stairs_inv` | 20% | step height: 5 cm → 23 cm | Descending inverted pyramid — robot must step down into a pit |
| `boxes` | 20% | box height: 5 cm → 20 cm | Grid of randomly-sized raised blocks spread across the tile |
| `random_rough` | 20% | noise amplitude: 2 cm → 10 cm | Heightfield with random uniform noise — uneven bumpy ground |
| `hf_pyramid_slope` | 10% | slope angle: 0° → ~22° | Smooth pyramid ramp — robot must navigate a continuous slope |
| `hf_pyramid_slope_inv` | 10% | slope angle: 0° → ~22° | Inverted smooth pyramid — robot must descend into a concave slope |

Each tile is **8 m × 8 m**. The full terrain grid is **10 rows × 20 columns**, giving 200 tiles in total. The difficulty parameter for each terrain type scales **linearly from its minimum to its maximum** across the 10 rows — row 0 has the easiest version of each terrain, row 9 has the hardest.

---

## Training Method — Actor-Critic (PPO)

Training uses the **RSL-RL** library, which implements **Proximal Policy Optimisation (PPO)** with an **actor-critic** architecture:

- **Actor network**: takes the robot's observations (joint positions, joint velocities, base angular velocity, projected gravity, velocity commands, previous actions) and outputs joint position and wheel velocity targets.
- **Critic network**: takes a richer set of observations (same as actor plus privileged state) and estimates the expected return — the value function. It is used only during training to compute advantages; it is not deployed on the real robot.
- At each training step, the critic's value estimates are used to compute **generalised advantage estimates (GAE)**, which tell the actor which actions led to better-than-expected outcomes. The actor's policy is then updated via gradient ascent, clipped by PPO's trust-region constraint to prevent large destabilising updates.
- **4096 parallel environments** run simultaneously in simulation, collecting experience in parallel each step. This gives a large, diverse batch of transitions for each policy update.

---

## Terrain Difficulty Curriculum

Training does **not** use random terrain placement. Instead, a progressive curriculum is used so the robot develops skills on easier terrain before being exposed to harder terrain.

### How the curriculum is enabled

In `velocity_env_cfg.py`, the `CurriculumCfg` includes a `terrain_levels` term:

```python
terrain_levels = CurrTerm(func=mdp.terrain_levels_vel)
```

When this term is present (not `None`), the environment automatically sets:

```python
self.scene.terrain.terrain_generator.curriculum = True
```

This tells the terrain generator to arrange tiles in **ascending order of difficulty across rows** rather than randomly. Row 0 of every terrain type uses the minimum difficulty parameter; row 9 uses the maximum.

### Initial placement

At the start of training, each of the 4096 environments is assigned a **random starting level between 0 and 5** (inclusive):

```python
# terrain_importer.py
self.terrain_levels = torch.randint(0, max_init_level + 1, (num_envs,), device=self.device)
```

`max_init_terrain_level = 5` is set in the scene config, so no robot starts on the hardest half of the terrain grid. The upper levels (6–9) are unlocked only through earned progression during training.

### Progression and regression at each episode end

At the end of every episode, `terrain_levels_vel` evaluates **each environment independently** by measuring how far the robot physically travelled from its spawn point:

```python
# curriculums.py
distance = torch.norm(asset.data.root_pos_w[env_ids, :2] - env.scene.env_origins[env_ids, :2], dim=1)

move_up   = distance > terrain.cfg.terrain_generator.size[0] / 2   # walked > 4 m → promote
move_down = distance < torch.norm(command[env_ids, :2], dim=1) * max_episode_length_s * 0.5
```

- **Promote** (`move_up`): the robot walked more than 4 m — it successfully navigated the terrain. Its level increases by 1.
- **Demote** (`move_down`): the robot walked less than 50% of what the commanded velocity required — it struggled. Its level decreases by 1.
- **No change**: performance was in between.

This judgment is made for all 4096 envs simultaneously using vectorised tensor operations — no loop over individual robots.

### Spawning at the new level

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

### Summary of the full training loop

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

### Velocity command curriculum (disabled for B2W)

The framework also supports a separate curriculum that starts the commanded velocity range at 10% of maximum and widens it as the tracking reward improves. For the B2W task this is explicitly disabled:

```python
# rough_env_cfg.py
self.curriculum.command_levels_lin_vel = None
self.curriculum.command_levels_ang_vel = None
```

The B2W robot is therefore commanded to track velocities from the full range (`±1 m/s` linear, `±1 rad/s` angular) from the very first episode. Only the terrain difficulty is gated by the curriculum.
