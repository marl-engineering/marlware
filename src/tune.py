import logging
from logging import Logger
from typing import Tuple

import hydra
import ray
import wandb
from logger import TraceLogger
from node import deserialize_configuration_node
from omegaconf import DictConfig
from omegaconf import OmegaConf
from tuner import Tuner
from util import methods


def delegate_tuner(
    env_conf: str,
    configuration: OmegaConf,
    accelerator: str,
    trace_logger: Logger,
    *,
    num_workers: int,
    seed: int,
) -> Tuner:
    """delegate tuner w.r.t passed configuration"""
    tuner = Tuner(configuration)

    timestamp = methods.get_current_timestamp()
    run_identifier = f"marlware-run-qmix-{timestamp}"

    tuner.commit(
        env_conf=env_conf,
        accelerator=accelerator,
        logger=trace_logger,
        run_id=run_identifier,
        num_workers=num_workers,
        seed=seed,
    )
    return tuner


def access_trial_directives(configuration: OmegaConf) -> Tuple[OmegaConf, OmegaConf]:
    """access configuration and get runtime and device settings"""
    runtime = configuration.get("runtime", None)
    device = configuration.get("device", None)
    return runtime, device


def get_logger() -> logging.Logger:
    """get hydra logger"""
    log = logging.getLogger(__name__)
    return log


def format_config_file(cfg: OmegaConf) -> str:
    """reformat to yaml for a nice display and add a message"""
    message = "Starting Trial with Hydra Configuration ...\n"
    formatted_config = OmegaConf.to_yaml(cfg, resolve=True)
    return message + formatted_config


def start_wandb(cfg: DictConfig):
    """create wandb instance"""
    wandb.config = OmegaConf.to_container(cfg, resolve=True, throw_on_missing=True)
    run = wandb.init(entity=cfg.wandb.entity, project=cfg.wandb.project)
    return run


@hydra.main(version_base=None, config_path="conf", config_name="trial")
def runner(cfg: DictConfig) -> None:
    """execute trial"""
    logger = get_logger()
    formatted_config = format_config_file(cfg)
    logger.info(formatted_config)
    trace_logger = TraceLogger(logger)

    trainable_conf, trial_conf, environ_conf = deserialize_configuration_node(cfg)
    runtime, device = access_trial_directives(trial_conf)

    accelerator = device.get("accelerator", "cpu")
    seed = device.get("seed", None)
    num_workers = device.get("num_workers", 1)
    warmup = runtime.get("warmup", 0)

    tuner = delegate_tuner(
        environ_conf,
        trainable_conf,
        accelerator,
        trace_logger,
        num_workers=num_workers,
        seed=seed,
    )

    n_timesteps = runtime.n_timesteps
    batch_size = trainable_conf.buffer.batch_size
    eval_schedule = runtime.eval_schedule
    eval_n_games = runtime.n_games
    display_freq = runtime.display_freq

    if not ray.is_initialized():
        ray.init()

    try:
        tuner.optimize(
            n_timesteps,
            batch_size,
            warmup,
            eval_schedule,
            eval_n_games,
            display_freq,
        )
    except Exception as e:
        logger.info(f"Failed to optimize due to exception {e}")
        tuner.close_envs()
        ray.shutdown()


if __name__ == "__main__":
    runner()
