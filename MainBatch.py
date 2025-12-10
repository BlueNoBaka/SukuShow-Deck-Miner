import logging
import time
import os
import multiprocessing
import json

from platform import python_implementation
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from RChart import Chart
from DeckGen import generate_decks_with_sequential_priority_pruning
from DeckGen2 import generate_decks_with_double_cards
from CardLevelConfig import convert_deck_to_simulator_format, fix_windows_console_encoding, CARD_CACHE
from SkillResolver import SkillEffectType
from Simulator_core import run_game_simulation, MUSIC_DB

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

BONUS_SFL = 6.6
CENTERCHAR = None
LIMITBREAK_BONUS = {
    1: 1, 2: 1, 3: 1, 4: 1, 5: 1,
    6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
    11: 1.2,
    12: 1.3,
    13: 1.35,
    14: 1.4
}


def score2pt(results):
    card_limitbreak = dict()
    for deck in results:
        bonus = BONUS_SFL
        centercard = deck["center_card"]
        if centercard:
            limitbreak = card_limitbreak.get(centercard, None)
            if limitbreak == None:
                levels = CARD_CACHE[centercard]
                card_limitbreak[centercard] = limitbreak = max(levels[1:])
            bonus *= LIMITBREAK_BONUS[limitbreak]
        deck['pt'] = int(deck['score'] * bonus)  # 实际为向上取整而非截断
    return results


def save_simulation_results(results_data: list, filename: str = os.path.join("log", "simulation_results.json"), calc_pt=False):
    """
    将模拟结果数据保存到 JSON 文件，只保留最高分的顺序。
    results_data: 包含每个卡组及其得分的字典列表。
                  例如: [{"deck_cards": [id1, id2, ...], "score": 123456}, ...]
    filename: 保存 JSON 文件的名称。
    """

    unique_decks_best_scores = {}  # Key: tuple of sorted card IDs, Value: {'deck_card_ids': original_list, 'score': best_score}

    for result in results_data:
        current_deck_card_ids = result['deck_card_ids']
        current_score = result['score']
        center_card = result['center_card']

        # Create a standardized key for comparison (sorted tuple of card IDs)
        # Ensure card IDs are integers for consistent sorting if they are not already
        sorted_card_ids_tuple = tuple(sorted(map(int, current_deck_card_ids)))

        if sorted_card_ids_tuple not in unique_decks_best_scores or \
                current_score > unique_decks_best_scores[sorted_card_ids_tuple]['score']:
            # If this is a new unique combination or we found a higher score for it
            unique_decks_best_scores[sorted_card_ids_tuple] = {
                'deck_card_ids': current_deck_card_ids,
                'center_card': center_card,
                'score': current_score,
            }

    # Convert the unique decks dictionary back to a list of results
    processed_results = list(unique_decks_best_scores.values())
    if calc_pt:
        processed_results = score2pt(processed_results)
        # 合并既有log
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                processed_results.extend(json.load(f))
        processed_results.sort(key=lambda i: i["pt"], reverse=True)
    else:
        processed_results.sort(key=lambda i: i["score"], reverse=True)
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(processed_results, f, ensure_ascii=False, indent=0)
        logger.info(f"Simulation results saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving simulation results to JSON: {e}")


def task_generator_func(decks_generator, chart, player_level):
    """
    一个生成器函数，从 decks_generator 获取每个卡组，
    并将其转换为 run_game_simulation 所需的任务格式。
    """
    for i, (deck_card_ids_list, center_card) in enumerate(decks_generator):  # Simulate all decks as example
        sim_deck_format = convert_deck_to_simulator_format(deck_card_ids_list)
        yield (sim_deck_format, chart, player_level, i, deck_card_ids_list, center_card)


#  --- Main Execution Block for Parallel Simulation ---
if __name__ == "__main__":
    pypy_impl = python_implementation() == "PyPy"
    if pypy_impl:
        fix_windows_console_encoding()
    start_time = time.time()

    # --- Step 1: Define all valid cards ---

    # 模拟时实际使用的卡牌范围
    card_ids = [
        1011501,  # 沙知
        1021701, 1021702, 1021523, 1021512,  # 梢: LR 银河 舞会
        # 1021901, 
        1021801, 1021802,  # 梢: BR PE EA
        1022701, 1022702, # 1022504, 1022521,  # 缀: LR 明月 银河
        #1022901, 
        1022801, 1022802,  # 缀: BR PE EA
        1023702,  # 1023520,  # 慈: LR 银河
        # 1023901, 1023801, 1023802,  # 慈: BR PE EA
        1031530, 1031533,  # 1031519,  # 帆: IDOME 地平 舞会
        # 1031901, 
        1031801, 1031802, 1031803,  #帆: BR(2024) PE EA
        1032518, 1032528, 1032530, 1032532, # 沙: 舞会 IDOME 地平 Flash
        # 1032901, 
        1032801, 1032802, 1032803,  # 沙: BR PE EA OE
        1033514, 1033524, 1033525,  # 乃: 舞会 IDOME COCO夏
        1033526, 1033527, 1033528, 1033530,  # 乃: 喵信号 一生梦 地平 人偶
        # 1033901, 
        1033803, 1033801, 1033802,  # 乃: BR(2024) OE PE EA
        1041513, 
        1041512, 1041516, # 1041517,  # 吟: 舞会 梦烦 水果 花火
        1041901, 1041801, 1041802,  # 吟: BR EA OE
        1042515, 1042516, 1042518, 1042519, 1042801, 1042802,  # 铃: 暧昧 太阳 羽音 Flash EA OE
        1043515, 1043516, 1043519,  # 芽: BLAST COCO夏 VS 羽音
        # 1043902, 1043801, 1043802,  # 芽: BR(2025) EA OE    
        1051506, 1051901, 
        #1051503, 
        #1051505,  # 1051501, 1051502,  # 泉: 片翼 天地黎明 FC DB RF
        1052506, 1052901, 
        #1052503, 1052801, # 1052504  # 塞: 片翼 BR 十六夜 OE 天地黎明
    ]
    card_ids_22 = [
        1011501,  # 沙知
        1021523, #1021901, 
        1021512, 1021701,  # 梢: 银河 BR 舞会 LR
        #1022521, 
        1022701, #1022901, 1022504,  # 缀: 银河 LR BR 明月
        1023520, 1023701, 1023901,  # 慈: 银河 LR BR
        1031519, 1031901,  # 帆: 舞会 BR(2024)
        1032518, #1032901,  # 沙: 舞会 BR
        1033514, 1033525, 1033901,  # 乃: 舞会 COCO夏 BR
        1041513,  # 吟: 舞会
        #1042516, 1042801, 1042802, # 1042515, # 1042512,  # 铃: 太阳 EA OE 暧昧mayday 舞会
        1043515, 1043516, 1043801, 1043802,  # 芽: BLAST COCO夏 EA OE 舞会1043512
        1051503, #1051501, 1051502,  # 泉: 天地黎明 DB RF
        1052901, 1052503,  # 1052504  # 塞: BR 十六夜 天地黎明
    ]

    # --- 配置卡组限制条件 ---

    # 卡组必须包含以下全部卡牌
    mustcards_all = []
    # 卡组必须包含至少一张以下卡牌
    mustcards_any = []
    # 将以下卡牌移出备选池
    exclude = []
    # 卡组包含DR或LR时，仍可以作为C位的非DR/LR卡牌
    secondary_center = [1031533, 1032530, 1033528]
    # 若备选池中无DR，并且未指定其他卡牌作为C位卡牌，则会模拟所有可能的C位
    # 以上填写格式均为: [卡牌id1, 卡牌id2, ...]

    # 卡组必须包含以下所有技能类型
    mustskills_all = [
        # SkillEffectType.DeckReset,  # 洗牌
        SkillEffectType.ScoreGain,  # 分
        SkillEffectType.VoltagePointChange,  # 电
        SkillEffectType.NextAPGainRateChange,  # 分加成 (但是写作AP加成)
        SkillEffectType.NextVoltageGainRateChange,  # 电加成
        # SkillEffectType.APChange,  # 回复/扣除AP
        # SkillEffectType.MentalRateChange,  # 回复/扣除血量
        # SkillEffectType.CardExcept,  # 卡牌除外
    ]

    # --- Step 2: Prepare simulation tasks ---
    fixed_music_id = "405106"  # My Lucky Clover
    fixed_difficulty = "02"
    fixed_player_master_level = 50

    # 强制指定歌曲C位和颜色
    center_override = None  # 1032
    color_override = None  # 1 # 1=Smile 2=Pure 3=Cool

    # 新增：批次大小和临时文件目录
    BATCH_SIZE = 1_000_000  # 每100万条结果保存一个文件
    TEMP_OUTPUT_DIR = "temp"
    FINAL_OUTPUT_DIR = "log"

    try:
        pre_initialized_chart = Chart(MUSIC_DB, fixed_music_id, fixed_difficulty)
        pre_initialized_chart.ChartEvents = [(float(t), e) for t, e in pre_initialized_chart.ChartEvents]
        # pre_initialized_chart.ChartEvents = [(int(float(t) * 1_000_000) , e) for t, e in pre_initialized_chart.ChartEvents]

        if center_override:
            pre_initialized_chart.music.CenterCharacterId = center_override
        if color_override:
            pre_initialized_chart.music.MusicType = color_override
        logger.info(f"Chart for {pre_initialized_chart.music.Title} (ID: {fixed_music_id}) and Difficulty {fixed_difficulty} pre-initialized.")
    except Exception as e:
        logger.error(f"Failed to pre-initialize Chart object: {e}")
        exit()

    # BONUS_SFL = (len(pre_initialized_chart.music.SingerCharacterId) + 1) * 0.7 + 1
    CENTERCHAR = str(pre_initialized_chart.music.CenterCharacterId)

    # 移除除外池，并筛选C位角色的DR、LR
    card_ids = list(set(card_ids) - set(exclude))
    primary_center = set()
    other_center = set()
    for card in card_ids:
        card_str = str(card)
        if card_str[0:4] == CENTERCHAR:
            if card_str[4] in ["7", "8"]:
                primary_center.add(card)
            else:
                other_center.add(card)

    # 添加备用C位池中的可用卡牌
    center_char_id = pre_initialized_chart.music.CenterCharacterId
    for card in secondary_center:
        if card // 1000 == center_char_id and card in card_ids:
            primary_center.add(card)

    available_center = primary_center or other_center or set()
    if available_center:
        logger.info(f"Available center ({len(available_center)}): {available_center}")
    else:
        logger.info(f"Missing available center card")

    logger.info(f"Pre-calculating deck amount from {len(card_ids)} cards...")

    # 3. 获取卡组生成器
    decks_generator = generate_decks_with_double_cards(
        cardpool=card_ids,
        mustcards=[mustcards_all, mustcards_any, mustskills_all],
        center_char=center_char_id,  # 未指定center_char时会生成不含C位角色的卡组
        center_card=available_center,
        log_path=os.path.join("log", f"simulation_results_{fixed_music_id}_{fixed_difficulty}.json"),
    )
    total_decks_to_simulate = decks_generator.total_decks
    logger.info(f"{total_decks_to_simulate} decks to be simulated.")

    # 4. 创建模拟任务生成器
    # task_generator_func 会按需从 generated_decks_generator 中拉取卡组
    simulation_tasks_generator = task_generator_func(
        decks_generator, pre_initialized_chart, fixed_player_master_level
    )

    os.makedirs(TEMP_OUTPUT_DIR, exist_ok=True)
    os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

    # Use multiprocessing.Pool with imap_unordered
    num_processes = os.cpu_count() or 1
    logger.info(f"Starting parallel simulations using {num_processes} processes...")
    best_score = -1
    best_deck_info = None  # 存储最佳卡组的完整信息
    best_log = []

    current_batch_results = []  # 存储当前批次的结果
    temp_files = []            # 存储所有临时文件的路径
    batch_counter = 0          # 批次计数器
    results_processed_count = 0  # 已处理结果的总数

    with multiprocessing.Pool(processes=num_processes) as pool:
        # 若 CPU 占用率偏低，可以在此增加每次获取任务时给单个进程分配的卡组数量
        if pypy_impl:
            chunksize = 10000
        else:
            chunksize = 500
        results_iterator = pool.imap_unordered(run_game_simulation, simulation_tasks_generator, chunksize)
        with logging_redirect_tqdm():
            for result in tqdm(results_iterator, total=total_decks_to_simulate):
                current_score = result['final_score']
                original_index = result['original_deck_index']
                current_log = result["cards_played_log"]
                deck_card_ids = result['deck_card_ids']
                center_card = result['center_card']

                # 记录当前卡组的得分、卡牌、C位卡牌，添加到结果列表中
                current_batch_results.append({
                    "deck_card_ids": deck_card_ids,  # 使用卡牌ID列表
                    "center_card": center_card,
                    "score": current_score,
                })
                results_processed_count += 1

                if current_score > best_score:
                    best_score = current_score
                    best_deck_info = {
                        "original_index": original_index,
                        "deck_card_ids": deck_card_ids,
                        "center_card": center_card,
                        "score": current_score
                    }
                    best_log = current_log
                    logger.info(f"NEW HI-SCORE! Deck: {original_index}, Score: {current_score:,}")
                    logger.info(f"  Cards: {deck_card_ids}")
                    logger.info(f"  Center: {center_card}")

                if len(current_batch_results) >= BATCH_SIZE:
                    batch_counter += 1
                    temp_filename = os.path.join(TEMP_OUTPUT_DIR, f"temp_batch_{batch_counter:0>3}.json")
                    save_simulation_results(current_batch_results, temp_filename)
                    temp_files.append(temp_filename)
                    current_batch_results = []  # 清空当前批次列表

        # --- 处理最后一批可能不满BATCH_SIZE的结果 ---
        if current_batch_results:
            batch_counter += 1
            temp_filename = os.path.join(TEMP_OUTPUT_DIR, f"temp_batch_{batch_counter:0>3}.json")
            save_simulation_results(current_batch_results, temp_filename)
            temp_files.append(temp_filename)
            current_batch_results = []  # 清空

    end_time = time.time()
    logger.info("--- All simulations completed! ---")
    logger.info(f"Total simulation time: {end_time - start_time:.2f} seconds")

    # --- Step 4: Save all results to JSON ---
    if best_score != -1:
        all_simulation_results = []
        for temp_file in tqdm(temp_files, desc="Merging Files"):
            with open(temp_file, 'r') as f:
                all_simulation_results.extend(json.load(f))
            os.remove(temp_file)
        json_output_filename = os.path.join("log", f"simulation_results_{fixed_music_id}_{fixed_difficulty}.json")
        save_simulation_results(all_simulation_results, json_output_filename, calc_pt=True)

    # --- Step 5: Final Summary ---
    logger.info(f"\n--- Final Simulation Summary ---")
    logger.info(f"Map: {MUSIC_DB.get_music_by_id(fixed_music_id).Title} ({fixed_difficulty})")
    logger.info(f"Total simulations run: {results_processed_count}")
    if best_score != -1:
        logger.info(f"Best Score: {best_score:,}")
        logger.info(f"Best Deck: {best_deck_info['original_index']}\t Center: {best_deck_info['center_card']}")
        logger.info(f"Cards: {best_deck_info['deck_card_ids']}")
        best_log_str = [" | ".join(best_log[i:i + 3])
                        for i in range(0, len(best_log), 3)]
        best_log_str = '\n'.join(best_log_str)
        logger.info(f"Log ({len(best_log)}):")
        logger.info(best_log_str)
    else:
        logger.info("No simulations yielded a score.")
