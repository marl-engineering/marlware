import random
from typing import Dict
from typing import Optional
from typing import Tuple

import numpy as np
import torch
from smac.env import StarCraft2Env


# TODO: Refactor this shit class
class SC2Environ:
    """
    Abstraction layer for SC2 environment handler

    Args:
        :param [map_name]: map name for the sc2 env to render

    """

    def __init__(self, map_name: str) -> None:
        self._map_name = map_name

    def _rnd_seed(self, *, seed: Optional[int] = None):
        """set random seed"""
        if seed:
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)
            np.random.seed(seed)
            random.seed(seed)

    def create_env_instance(
        self, *, seed: Optional[int] = None
    ) -> Tuple[StarCraft2Env, Dict]:
        """create sc2 environ based on passed map name and return along with info"""
        self._rnd_seed(seed=seed)
        env = StarCraft2Env(map_name=self._map_name)
        env_info = env.get_env_info()
        return env, env_info
