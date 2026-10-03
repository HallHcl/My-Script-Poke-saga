"""MonsterBot Task Modules"""
from tasks.base_task import BaseTask
from tasks.task_tower_hard import TowerHardTask
from tasks.task_champion import ChampionTask
from tasks.task_daily_claim import DailyClaimTask

__all__ = ["BaseTask", "TowerHardTask", "ChampionTask", "DailyClaimTask"]
