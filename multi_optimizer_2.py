import json
import logging
import os
import time
import csv
from tqdm import tqdm
from CardLevelConfig import fix_windows_console_encoding

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,  # Adjust logging level as needed (e.g., INFO, DEBUG)
    format='%(message)s'
)

# === 配置 ===
# 配置求解歌曲，格式: ("歌曲ID", "难度"),
# 求解前需运行 MainBatch.py 生成对应的卡组得分记录
CHALLENGE_SONGS = [
    # 若只输入两首歌则会寻找仅针对两面的最优解，不考虑第三面
    ("405106", "02"),  # My Lucky Clover
    ("405127", "02"),  # Hip, hip, hooray!
    ("105103", "02"),  # チリコンカン
]

# 每首歌只保留得分排名前 N 名的卡组用于求解
TOP_N = 50000

# 在控制台与文件输出中显示卡牌名称
SHOWNAME = True

# 寻找最优解时忽略包含特定卡牌的卡组 (三面均生效)
# 填写格式为: [卡牌id1, 卡牌id2, ...]
FORBIDDEN_CARD = []

def get_song_title() -> dict:
    try:
        with open("Musics.csv", 'r', encoding="UTF-8-sig") as f:
            csv_data = csv.DictReader(f)
            titles = {}
            for row in csv_data:
                titles[row["Id"]] = row["Song"]
        return titles
    except FileNotFoundError:
        logger.error(f"Error: Musics.csv not found")
        return None


def get_card_name() -> dict:
    try:
        with open("CardData.csv", 'r', encoding="UTF-8-sig") as f:
            csv_data = csv.DictReader(f)
            cards = {}
            nbsp = "\xa0"
            for row in csv_data:
                fullname = f"[{row['Name']}] {row['Character']}".replace(nbsp, ' ')
                cards[int(row["CardId"])] = fullname
        return cards
    except FileNotFoundError:
        logger.error(f"Error: CardData.csv not found")
        return None


if __name__ == "__main__":
    fix_windows_console_encoding()

    start_time = time.time()

    level_files = []
    for music_id, difficulty in CHALLENGE_SONGS:
        level_files.append(os.path.join("log", f"simulation_results_{music_id}_{difficulty}.json"))

    # === 读取与准备数据 ===
    logger.info("Preparing data...")
    levels_raw = []
    all_cards = set()

    title = get_song_title()
    if SHOWNAME:
        cardname = get_card_name()
    for i, f in enumerate(level_files):
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            total = len(data)
            data.sort(key=lambda x: x["pt"], reverse=True)
            data = data[:TOP_N]
            levels_raw.append(data)
            for deck in data:
                all_cards.update(deck["deck_card_ids"])
        song_id, difficulty = CHALLENGE_SONGS[i]
        logger.info(f"Loaded top {TOP_N} of {total} results for {song_id}_{difficulty} ({title.get(song_id, '？？？')})")

    # 仅针对两首歌曲求解时，第三首歌填充假数据
    if len(CHALLENGE_SONGS) == 2:
        levels_raw.append([{
            "deck_card_ids": [],
            "score": 0,
            "pt": 0
        }])

    # === 根据每关最高 Pt 重新排序（默认按大、小、中顺序）===
    if len(CHALLENGE_SONGS) == 3:
        best = [deck[0]["pt"] for deck in levels_raw]
        i_max = max(range(3), key=lambda i: best[i])
        i_min = min(range(3), key=lambda i: best[i])
        i_mid = 3 - i_max - i_min
        sorted_indices = [i_max, i_min, i_mid]
        # 重排 CHALLENGE_SONGS 和 levels_raw
        CHALLENGE_SONGS = [CHALLENGE_SONGS[i] for i in sorted_indices]
        levels_raw = [levels_raw[i] for i in sorted_indices]
        logger.info(f"Challenge songs reordered for optimization: {CHALLENGE_SONGS}")

    # === 建立卡牌ID到bit位的映射 ===
    card_to_bit = {cid: i for i, cid in enumerate(sorted(all_cards))}
    logger.info(f"Loaded {len(card_to_bit)} unique cards")
    assert len(card_to_bit) <= 64, "卡牌种类超过64张时需使用更复杂的bitarray方案"
    assert len(card_to_bit) >= 6 * len(CHALLENGE_SONGS), "可用卡牌过少，必定出现重复卡牌"

    # === 转换deck为bitmask ===
    def deck_to_mask(deck):
        mask = 0
        for cid in deck["deck_card_ids"]:
            mask |= 1 << card_to_bit[cid]
        return mask

    levels = []
    for data in levels_raw:
        decks = []
        for i, deck in enumerate(data, start=1):
            # 忽略包含特定卡牌的卡组
            if any(cid in deck["deck_card_ids"] for cid in FORBIDDEN_CARD):
                    continue
            decks.append({
                "mask": deck_to_mask(deck),
                "rank": i,
                "score": deck["score"],
                "pt": deck["pt"],
                "deck": deck["deck_card_ids"]
            })
        levels.append(decks)

    logger.info("Starting deck optimization...")
    # === 主搜索逻辑 ===
    best_pt = -1
    best_combo = None

    # 三重循环 + 多级剪枝
    for i1, deck1 in tqdm(enumerate(levels[0]), total=len(levels[0]), desc="Song 1", leave=True, position=0):
        mask1, pt1 = deck1["mask"], deck1["pt"]

        # 上限剪枝：即便选取剩下两关最高pt，也不可能超过best_pt
        max_possible = pt1 + levels[1][0]["pt"] + levels[2][0]["pt"]
        if max_possible <= best_pt:
            break

        for i2, deck2 in enumerate(levels[1]):
            mask2, pt2 = deck2["mask"], deck2["pt"]

            # 检查冲突
            if mask1 & mask2:
                continue

            pt12 = pt1 + pt2

            # 第二层剪枝：deck3最高pt都不够超越当前最优
            if pt12 + levels[2][0]["pt"] <= best_pt:
                break

            for i3, deck3 in enumerate(levels[2]):
                mask3, pt3 = deck3["mask"], deck3["pt"]

                # 冲突检测
                if (mask1 | mask2) & mask3:
                    continue

                total_pt = pt12 + pt3

                if total_pt > best_pt:
                    best_pt = total_pt
                    best_combo = (deck1, deck2, deck3)
                    logger.info(f"New best total pt found: {best_pt:,}")
                    for i, d in enumerate(best_combo):
                        if i >= len(CHALLENGE_SONGS):
                            break
                        logger.info(f"  Song {i+1} {CHALLENGE_SONGS[i]}: ")
                        logger.info(f"    Pt: {d['pt']:,}\tScore: {d['score']:,}\tRank: {d['rank']}")
                        logger.info(f"    Deck (ID): {d['deck']}")
                else:
                    break

    end_time = time.time()
    logger.info("--- Optimization completed! ---")
    logger.info(f"Total time: {end_time - start_time:.2f} seconds \n")

    # === 输出结果 ===
    output = []
    output.append("=== Best Combination ===")

    if best_pt > 0:
        output.append(f"Total Pt: {best_pt:16,}")
        for i, d in enumerate(best_combo):
            if i < len(CHALLENGE_SONGS):
                song_id, difficulty = CHALLENGE_SONGS[i]
                output.append(f"  Song {i+1} | {song_id} ({difficulty}) | {title.get(song_id, '？？？')}")
                output.append(f"    Score: {d['score']:15,}")
                output.append(f"    Pt: {d['pt']:18,}\tRank: {d['rank']}")
                output.append(f"    Deck (ID): {d['deck']}")
                if SHOWNAME:
                    output.append(f"    {[cardname.get(cid, '？？？') for cid in d['deck'][:3]]}")
                    output.append(f"    {[cardname.get(cid, '？？？') for cid in d['deck'][3:]]}")
        output = "\n".join(output)
        logger.info(f"{output}")
        with open("best_3_song_combo.txt", "w", encoding="utf-8") as f:
            f.write(output)
            f.write("\n")
        logger.info(f"Best 3-song combination saved to best_3_song_combo.txt")
    else:
        logger.info("No valid 3-deck combination found.")
