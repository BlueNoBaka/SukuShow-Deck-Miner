import logging
import os
from enum import Enum
# 导入所有 R 模块和 db_load 函数
from RCardData import db_load
from RChart import Chart, MusicDB
from RDeck import Deck
from RLiveStatus import PlayerAttributes
from SkillResolver import UseCardSkill, ApplyCenterSkillEffect, ApplyCenterAttribute, CheckCenterSkillCondition
from CardLevelConfig import DEATH_NOTE

# --- Configure logging (for the module itself if needed, or rely on main script's config) ---
# 注意：子进程会继承父进程的logger配置，但为了独立运行和测试，可以保留或简化这里的logger
logger = logging.getLogger(__name__)

# --- Global DBs for the simulator module ---
# 这些DBs也应该在模块的顶层被加载，确保它们在子进程中是可访问的
try:
    MUSIC_DB = MusicDB()
    DB_CARDDATA = db_load(os.path.join("Data", "CardDatas.json"))
    DB_SKILL = db_load(os.path.join("Data", "RhythmGameSkills.json"))
    DB_SKILL.update(db_load(os.path.join("Data", "CenterSkills.json")))
    DB_SKILL.update(db_load(os.path.join("Data", "CenterAttributes.json")))
    logger.info("Simulator core databases loaded.")
except ImportError as e:
    logger.error(f"Failed to import required R modules in simulator_core. Error: {e}")
    # Consider raising an exception or having a fallback
except FileNotFoundError as e:
    logger.error(f"Required database file not found: {e}. Please check your 'Data' directory.")
    # Exit or handle gracefully if critical modules are missing/DBs not found
    exit(1)  # Exit with an error code


def run_game_simulation(
    task_args: tuple  # This will be (deck_card_data, chart_obj, player_master_level, original_deck_index)
) -> dict:
    """
    Runs a single game simulation and includes the original deck index in the result.
    Designed to be run in parallel.

    Args:
        deck_card_data (list[tuple[int, list[int]]]): A list of tuples, where each tuple
            is (CardSeriesId, [card_level, center_skill_level, skill_level]).
            Example: [(1011501, [120, 1, 12]), ...]
        chart_obj (Chart): The music chart to simulate (e.g., Chart(MUSIC_DB, "103105", "02").
        player_master_level (int): The player's master level. 1 ~ 50.

    Returns:
        dict: A dictionary containing key simulation results (e.g., final score, card log).
              You can expand this to return more detailed metrics.
    """
    # NOTE: DBs (MUSIC_DB, DB_CARDDATA, DB_SKILL) are now global to this module
    # and inherited by child processes (copy-on-write).
    deck_card_data, chart_obj, player_master_level, original_deck_index, deck_card_ids = task_args

    d = Deck(DB_CARDDATA, DB_SKILL, deck_card_data)
    c: Chart = chart_obj
    player = PlayerAttributes(masterlv=player_master_level)
    player.set_deck(d)

    centercard = None
    afk_mental = 0
    for card in d.cards:
        cid = int(card.card_id)
        if cid in DEATH_NOTE:
            afk_mental = DEATH_NOTE[cid]
        if card.characters_id == c.music.CenterCharacterId:
            centercard = card
            for target, effect in centercard.get_center_attribute():
                ApplyCenterAttribute(player, effect, target)

    d.appeal_calc(c.music.MusicType)

    # Use a heap for ChartEvents for better performance
    import heapq
    event_heap = []
    for ts_str, event_name in c.ChartEvents:
        heapq.heappush(event_heap, (float(ts_str), event_name))

    heapq.heappush(event_heap, (player.cooldown, "CDavailable"))

    combo_count = 0
    cardnow = d.topcard()

    while event_heap:
        timestamp, event = heapq.heappop(event_heap)

        match event:
            case "Single" | "Hold" | "HoldMid" | "Flick" | "Trace":
                combo_count += 1
                if combo_count in []:
                    player.combo_add("GOOD", c.AllNoteSize)
                elif afk_mental and player.mental.get_rate() >= afk_mental:
                    player.combo_add("MISS", c.AllNoteSize, event)
                elif combo_count in []:
                    player.combo_add("GREAT", c.AllNoteSize)
                else:
                    player.combo_add("PERFECT", c.AllNoteSize)

                if player.CDavailable and cardnow and player.ap >= cardnow.cost:
                    player.ap -= cardnow.cost
                    conditions, effects = d.topskill()
                    UseCardSkill(player, effects, conditions, cardnow)
                    player.CDavailable = False
                    cdtime_float = timestamp + player.cooldown
                    heapq.heappush(event_heap, (cdtime_float, "CDavailable"))
                    cardnow = d.topcard()

            case "CDavailable":
                player.CDavailable = True
                if cardnow and player.ap >= cardnow.cost:
                    player.ap -= cardnow.cost
                    conditions, effects = d.topskill()
                    UseCardSkill(player, effects, conditions, cardnow)
                    player.CDavailable = False
                    cdtime_float = timestamp + player.cooldown
                    heapq.heappush(event_heap, (cdtime_float, "CDavailable"))
                    cardnow = d.topcard()

            case "LiveStart" | "LiveEnd" | "FeverStart":
                if event == "FeverStart":
                    player.fevertime = True
                if centercard is not None:
                    for condition, effect in centercard.get_center_skill():
                        if CheckCenterSkillCondition(player, condition, centercard, event):
                            ApplyCenterSkillEffect(player, effect)
                if event == "LiveEnd":
                    break

            case "FeverEnd":
                player.fevertime = False
            case _:
                pass

    return {
        "final_score": player.score,
        "cards_played_log": d.card_log,
        "original_deck_index": original_deck_index,
        "deck_card_ids": deck_card_ids
    }
