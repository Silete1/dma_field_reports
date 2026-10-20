from . import models
from . import wizards


def post_init_hook(env):
    from .models.dma_fr_seed import seed_value_maps

    seed_value_maps(env)
