from isaacsim import SimulationApp

app = SimulationApp({"headless": False})

import numpy as np
from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicSphere

world = World()
world.scene.add_default_ground_plane()
world.scene.add(DynamicSphere(prim_path="/World/sphere", position=np.array([0, 0, 2.0]), radius=0.2))

world.reset()
while app.is_running():
    world.step(render=True)

app.close()
