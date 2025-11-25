import zlib
import json
import yaml
import csv
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional  # Import necessary types

logger = logging.getLogger(__name__)


@dataclass
class Music:
    # Essential attributes, enforce types for better safety
    Id: int
    OrderId: int
    Title: str
    JacketId: int
    SoundId: int
    MusicType: int
    PlayTime: int  # Duration in milliseconds, based on your example

    # Optional attributes or those with default values
    TitleFurigana: str = ""
    Description: str = ""
    GenerationsId: Optional[int] = None
    UnitId: Optional[int] = None
    CenterCharacterId: Optional[int] = None
    # SingerCharacterId and SupportCharacterId are comma-separated strings
    # in YAML, need to parse them into lists of integers.
    # Parsed in __post_init__.
    SingerCharacterId: List[int] = field(default_factory=list)
    SupportCharacterId: List[int] = field(default_factory=list)

    ExperienceType: Optional[int] = None
    BeatPointCoefficient: Optional[int] = None
    ApIncrement: Optional[int] = None
    SongTime: Optional[int] = None
    FeverSectionNo: Optional[int] = None
    PreviewStartTime: Optional[int] = None
    PreviewEndTime: Optional[int] = None
    PreviewFadeInTime: Optional[int] = None
    PreviewFadeOutTime: Optional[int] = None
    ReleaseConditionType: Optional[int] = None
    ReleaseConditionDetail: Optional[int] = None
    ReleaseConditionText: str = ""
    StartTime: Optional[datetime] = None
    EndTime: Optional[datetime] = None
    MaxAp: Optional[int] = None
    IsVideoMode: Optional[int] = None
    VideoBgId: Optional[int] = None
    SongType: Optional[int] = None
    MusicScoreReleaseTime: Optional[datetime] = None

    # Process comma-separated IDs
    def __post_init__(self):
        if isinstance(self.SingerCharacterId, str):
            try:
                self.SingerCharacterId = [int(x.strip()) for x in self.SingerCharacterId.split(',') if x.strip()]
            except ValueError:
                self.SingerCharacterId = []  # Handle cases where string is not valid integers

        if isinstance(self.SupportCharacterId, str):
            try:
                self.SupportCharacterId = [int(x.strip()) for x in self.SupportCharacterId.split(',') if x.strip()]
            except ValueError:
                self.SupportCharacterId = []  # Handle cases where string is not valid integers


class MusicDB:
    def __init__(self, yaml_filepath: str = os.path.join("Data", "Musics.yaml")) -> None:
        self.db: List[Music] = []  # Stores all Music objects
        self._id_map: Dict[int, Music] = {}  # Optimized for ID lookups

        if not os.path.exists(yaml_filepath):
            raise FileNotFoundError(f"Music database file not found at: {yaml_filepath}")

        with open(yaml_filepath, encoding="UTF-8") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)

        if not isinstance(data, list):
            raise ValueError(f"Expected a list of music entries in {yaml_filepath}, but got {type(data)}")

        for info_dict in data:
            try:
                music_obj = Music(**info_dict)
                self.db.append(music_obj)
                self._id_map[music_obj.Id] = music_obj  # Populate ID map for O(1) lookup
            except TypeError as e:
                logger.debug(f"Warning: Could not create Music object from data {info_dict}. Error: {e}")
                # Log or handle missing/invalid required fields

    def get_music_by_id(self, music_id: int | str) -> Optional[Music]:
        """
        Retrieves a Music object by its ID.
        Args:
            music_id (int | str): The ID of the music.
        Returns:
            Optional[Music]: The Music object if found, otherwise None.
        """
        if isinstance(music_id, str):
            try:
                music_id = int(music_id)
            except ValueError:
                return None  # Invalid ID format

        return self._id_map.get(music_id)  # O(1) lookup

    def find_music_ids(self, **filters) -> List[int]:
        """
        Finds music IDs that match all provided filter criteria.

        Args:
            **filters: Keyword arguments where key is the attribute name
                       and value is the desired attribute value.
                       Special handling for list attributes like 'SingerCharacterId'.
                       Example: find_music_ids(MusicType=1, SingerCharacterId=1021)

        Returns:
            List[int]: A list of IDs of matching songs.
        """
        matching_ids: List[int] = []
        for music in self.db:
            match = True
            for attr, value in filters.items():
                if not hasattr(music, attr):
                    match = False
                    break  # Attribute does not exist on this music object

                music_attr_value = getattr(music, attr)

                if isinstance(music_attr_value, list):
                    # Special handling for list attributes (e.g., SingerCharacterId)
                    # If the filter value is an int, check if it's in the list
                    if isinstance(value, int):
                        if value not in music_attr_value:
                            match = False
                            break
                    # If the filter value is a list, check if all filter values are in the music's list
                    elif isinstance(value, list):
                        if not all(item in music_attr_value for item in value):
                            match = False
                            break
                    else:  # If filter value is other type for a list attribute, no match
                        match = False
                        break
                elif music_attr_value != value:  # Direct comparison for non-list attributes
                    match = False
                    break

            if match:
                matching_ids.append(music.Id)
        return matching_ids

    def find_music(self, **filters) -> List[Music]:
        """
        Finds Music objects that match all provided filter criteria.

        Args:
            **filters: Keyword arguments where key is the attribute name
                       and value is the desired attribute value.

        Returns:
            List[Music]: A list of matching Music objects.
        """
        matching_music: List[Music] = []
        for music in self.db:
            match = True
            for attr, value in filters.items():
                if not hasattr(music, attr):
                    match = False
                    break  # Attribute does not exist on this music object

                music_attr_value = getattr(music, attr)

                if isinstance(music_attr_value, list):
                    # Special handling for list attributes (e.g., SingerCharacterId)
                    if isinstance(value, int):
                        if value not in music_attr_value:
                            match = False
                            break
                    elif isinstance(value, list):
                        if not all(item in music_attr_value for item in value):
                            match = False
                            break
                    else:
                        match = False
                        break
                elif music_attr_value != value:
                    match = False
                    break

            if match:
                matching_music.append(music)
        return matching_music


class NoteTypes(Enum):
    """
    Note类型
    """
    Single = 0
    Hold = 1
    Flick = 2
    Trace = 3


class Note:
    def __init__(self, **kwargs) -> None:
        self.just: str
        self.holds: list[str] = []
        self.Uid: int
        self.Flags: int
        self.Type: int
        self.StartPos: tuple[int, int]
        self.EndPos: tuple[int, int]
        self.prev_note: Note = None
        self.next_note: Note = None
        self.__dict__.update(kwargs)
        self._parse_flags(self.Flags)

    def __str__(self) -> str:
        return (f"Uid: {self.Uid}\t Type: {self.Type}\n"
                f"Just: {self.just}\t"
                f"Holds: {self.holds}\n"
                f"Pos: {self.StartPos} -> {self.EndPos}")

    def _parse_flags(self, flags_value, is_mirror=False):
        """
        Precisely interprets the ulong Flags value using the NoteFlagsResolver structure
        and applies mirroring if specified.

        Args:
            flags_value (int): The ulong Flags value from the chart data.
            is_mirror (bool): Whether to apply the mirroring transformation.
        """

        # Extract the raw values based on the bit positions confirmed from assembly
        resolved_flags = {
            "Type": (flags_value >> 0) & 0xF,   # 4 bits
            "R1_raw": (flags_value >> 4) & 0x3F,  # 6 bits (0x3F = 63, which is 2^6 - 1)
            "R2_raw": (flags_value >> 10) & 0x3F,  # 6 bits
            "L1_raw": (flags_value >> 16) & 0x3F,  # 6 bits
            "L2_raw": (flags_value >> 22) & 0x3F,  # 6 bits
        }

        # Initialize the final values
        Type = resolved_flags["Type"]
        R1 = resolved_flags["R1_raw"]
        R2 = resolved_flags["R2_raw"]
        L1 = resolved_flags["L1_raw"]
        L2 = resolved_flags["L2_raw"]

        # Apply mirroring logic if is_mirror is True
        if is_mirror:
            # Constant for mirroring transformation
            mirror_const = 59  # From W10, #0x3B

            # New R1 becomes (59 - L1_raw), New L1 becomes (59 - R1_raw)
            R1_mirrored = mirror_const - L1
            L1_mirrored = mirror_const - R1

            # New R2 becomes (59 - L2_raw), New L2 becomes (59 - R2_raw)
            R2_mirrored = mirror_const - L2
            L2_mirrored = mirror_const - R2

            # Assign the mirrored values
            R1 = R1_mirrored
            L1 = L1_mirrored
            R2 = R2_mirrored
            L2 = L2_mirrored

        # Return the final interpreted flags
        self.Type = Type
        self.StartPos = (L1, R1)
        self.EndPos = (L2, R2)


class Chart:
    def __init__(self, db: MusicDB, MusicId, Tier) -> None:
        self.AllNoteSize: int = 0
        self.ChartNoteUnit: list[Note] = []
        self.ChartNoteTime: list[str] = []
        self.ChartEvents: list[(str, str)] = []
        self.FeverStartTime: float = 0
        self.FeverEndTime: float = 0
        self.music = db.get_music_by_id(MusicId)
        self.tier = Tier
        self.bpm = []
        self._loadbytes(Tier)
        self._loadcsv()
        self._initevents()

    def _loadbytes(self, Tier):
        bytes_path = os.path.join("Data", "bytes", f"rhythmgame_chart_{self.music.Id}_{Tier}.bytes")
        try:
            with open(bytes_path, 'rb') as f:
                compressed_data = f.read()

            try:
                decompressed_json_bytes = zlib.decompress(compressed_data, wbits=-15)
            except zlib.error as e:
                logger.debug(f"Error during zlib decompression: {e}")
                return None

            try:
                json_string = decompressed_json_bytes.decode('utf-8')
            except UnicodeDecodeError as e:
                logger.debug(f"Error decoding decompressed bytes to UTF-8: {e}")
                logger.debug("The decompressed data might not be valid UTF-8, or the JSON is corrupted.")
                return None

            try:
                chart_data = json.loads(json_string)
            except json.JSONDecodeError as e:
                logger.debug(f"Error parsing JSON: {e}")
                logger.debug("The decompressed string is not valid JSON.")
                # Print a snippet to help debug
                logger.debug(f"JSON snippet (first 500 chars):\n{json_string[:500]}...")
                return None

        except FileNotFoundError:
            logger.debug(f"Error: Chart file not found at '{bytes_path}'")
            return None
        except Exception as e:
            logger.debug(f"An unexpected error occurred during chart parsing: {e}")
            return None

        for bpm_data in chart_data["Bpms"]:
            self.bpm.append(bpm_data)

        for note_data in chart_data["Notes"]:
            self.ChartNoteUnit.append(Note(**note_data))

        hold_notes: list[Note] = []
        for note in self.ChartNoteUnit:
            if note.Type == 1:
                hold_notes.append(note)

        NOTE_ERROR = 0.00010001  # 避免实际差值0.1但浮点精度下的差值>0.1极端情况
        for index, note in enumerate(hold_notes):
            end_time = float(note.holds[-1])
            for note_next in hold_notes[index + 1:]:
                next_start_time = float(note_next.just)
                if end_time < next_start_time - NOTE_ERROR:
                    break
                elif abs(end_time - next_start_time) < NOTE_ERROR and note.EndPos == note_next.StartPos:
                    note.next_note = note_next
                    note_next.prev_note = note
                    break

        self._merge_holds()

        for note in self.ChartNoteUnit:
            self.ChartNoteTime.append(note.just)
            self.ChartNoteTime += note.holds
        self.AllNoteSize = len(self.ChartNoteTime)
        self.ChartNoteTime.sort(key=float)

    def _loadcsv(self):
        csv_path = os.path.join("Data", "csv", f"musicscore_{self.music.Id}.csv")
        try:
            with open(csv_path, 'r', encoding="UTF-8") as f:
                csv_data = csv.DictReader(f)
                section = []
                for row in csv_data:
                    if row["key_type"] == "20":
                        section.append(int(row["song_time"]))

        except FileNotFoundError:
            logger.debug(f"Error: Musicscore file not found at '{csv_path}'")
            return None
        except Exception as e:
            logger.debug(f"An unexpected error occurred during musicscore parsing: {e}")
            return None

        fever = self.music.FeverSectionNo

        self.FeverStartTime = section[fever - 2] / 1000
        if fever == 5:
            self.FeverEndTime = self.music.PlayTime / 1000
        else:
            self.FeverEndTime = section[fever - 1] / 1000

    def _initevents(self):
        self.ChartEvents.append(("0", "LiveStart"))
        self.ChartEvents.append((str(self.FeverStartTime), "FeverStart"))
        for note in self.ChartNoteUnit:
            self.ChartEvents.append((note.just, NoteTypes(note.Type).name))
            for index, timestamp in enumerate(note.holds, 1):
                if index != len(note.holds):
                    self.ChartEvents.append((timestamp, "HoldMid"))
                else:
                    self.ChartEvents.append((timestamp, "Hold"))

        self.ChartEvents.append((str(self.FeverEndTime), "FeverEnd"))
        self.ChartEvents.append((str(self.music.PlayTime / 1000), "LiveEnd"))

        self.ChartEvents.sort(key=lambda event: float(event[0]))

    def _GetHolds_multi_bpm(self, start_time: float, end_time: float) -> list[float]:
        """
        针对可变bpm的长条判定点计算，bpm恒定歌曲通用
        Calculates intermediate hold note timings between a start and end time,
        stepping at half-beat intervals, assuming a constant BPM.
        过长的多段长条在多次计算后会产生大于0.0001的累积误差
        可能导致整段算出来的判定点比实际少一个，暂时无解
        会少的都是后两个判定点只差0.0002秒内的缺德判定
        数量不多考虑针对性补点人工修正？

        Args:
            start_time (float): The start time of the hold note (in seconds).
            end_time (float): The end time of the hold note (in seconds).

        Returns:
            list[float]: A list of float timestamps representing the intermediate
                        points of the hold note, including the final end_time.
                        Returns an empty list if start_time >= end_time.
        """
        holds: list[float] = []

        start_time = float(start_time)
        end_time = float(end_time)

        # Handle invalid input or zero-duration holds
        if start_time >= end_time:
            return holds

        bpm_now = 0
        for data in self.bpm:
            if data["Time"] < start_time:
                bpm_now = data["Bpm"]
            else:
                break

        # Calculate the duration of a single beat in seconds
        seconds_per_beat = 60.0 / bpm_now

        # Calculate the duration of a half-beat (our step size)
        half_beat_duration = seconds_per_beat * 0.5

        current_time = start_time

        # Use the game's exact NoteError for floating-point comparisons
        # This comes from RhythmGameConsts.NoteError = 0.0001
        NOTE_ERROR = 0.00010001  # <--- 避免实际差值0.1但浮点精度下差值>0.1的极端情况

        current_time += half_beat_duration
        while current_time < end_time - NOTE_ERROR:

            # Add the current time to our list
            holds.append(f"{current_time:.7g}")

            # Move to the next half-beat
            current_time += half_beat_duration

            # Optional: Break if we've significantly overshot the end_time
            # This prevents excessive additions if `half_beat_duration` is large
            # and `current_time` jumps far past `end_time`.
            # Note: The original game's `GetHolds` also checks `LooseEquals` at the boundary.
            # This explicit check handles cases where `current_time` lands almost exactly on `end_time`.
            if abs(current_time - end_time) < NOTE_ERROR:
                break  # If we're very close to the end, stop adding and let the final append handle it.

            if current_time > end_time + NOTE_ERROR and holds:
                break  # If we overshot significantly, stop.

        # Always ensure the exact end_time is included as the last point
        # This matches the behavior observed in the decompiled code.
        # We also check for approximate equality to avoid adding duplicate end_time if it was the last point
        # added by the loop because it landed exactly on `end_time`.
        if not holds or abs(float(holds[-1]) - end_time) > NOTE_ERROR:
            holds.append(f"{end_time:.7g}")

        return holds

    def _generate_flags(self, Type: int, StartPos: tuple[int, int], EndPos: tuple[int, int], is_mirror: bool = False) -> int:
        """
        Generates the ulong flags_value from Type, StartPos, EndPos, and mirroring status.
        This is the reverse operation of the _parse_flags method.

        Args:
            Type (int): The Type value (0-15).
            StartPos (tuple[int, int]): A tuple (L1, R1) representing the StartPos.
                                        L1 and R1 should be in the range 0-63.
            EndPos (tuple[int, int]): A tuple (L2, R2) representing the EndPos.
                                    L2 and R2 should be in the range 0-63.
            is_mirror (bool): Whether mirroring transformation was applied when generating the flags.

        Returns:
            int: The reconstructed ulong flags_value.

        Raises:
            ValueError: If input values are out of their valid bit ranges.
        """

        # Validate input ranges
        if not (0 <= Type <= 15):
            raise ValueError(f"Type ({Type}) must be between 0 and 15 (inclusive).")

        for pos_val in StartPos + EndPos:
            if not (0 <= pos_val <= 63):
                raise ValueError(f"Position values ({pos_val}) in StartPos/EndPos must be between 0 and 63 (inclusive).")

        # Extract L1, R1, L2, R2 from StartPos and EndPos
        L1, R1 = StartPos
        L2, R2 = EndPos

        # If mirroring was applied during the original generation, we need to reverse it
        # to get the raw values that were actually stored in the flags.
        if is_mirror:
            mirror_const = 59

            R1_raw_from_mirrored_L1 = mirror_const - L1  # The input L1 was the R1_mirrored
            L1_raw_from_mirrored_R1 = mirror_const - R1  # The input R1 was the L1_mirrored

            R2_raw_from_mirrored_L2 = mirror_const - L2  # The input L2 was the R2_mirrored
            L2_raw_from_mirrored_R2 = mirror_const - R2  # The input R2 was the L2_mirrored

            # Assign these raw values to be used in the bit packing
            R1 = R1_raw_from_mirrored_L1
            L1 = L1_raw_from_mirrored_R1
            R2 = R2_raw_from_mirrored_L2
            L2 = L2_raw_from_mirrored_R2

        # Reconstruct the flags_value using bitwise OR
        # Each component is shifted left by its respective bit position
        # and then OR'ed together.

        flags_value = 0
        flags_value |= (Type & 0xF) << 0       # 4 bits for Type
        flags_value |= (R1 & 0x3F) << 4       # 6 bits for R1_raw
        flags_value |= (R2 & 0x3F) << 10      # 6 bits for R2_raw
        flags_value |= (L1 & 0x3F) << 16      # 6 bits for L1_raw
        flags_value |= (L2 & 0x3F) << 22      # 6 bits for L2_raw

        return flags_value

    def _merge_holds(self) -> list[Note]:
        """
        遍历音符列表，将已链接的Hold音符链合并为一个逻辑音符，
        并使用GetHolds生成其内部时间点。

        Returns:
            list[Note]: 转换后的音符列表，其中每个Hold音符链都被替换为一个
                        新的、包含所有步进点的逻辑Hold音符。
        """
        processed_note_ids = set()  # 用于跟踪已经处理过的音符ID，避免重复处理
        merged_notes: list[Note] = []

        # 按照音符的起始时间进行排序，以确保按顺序处理链条
        # 这是重要的，因为我们从链的开头开始遍历
        for note in self.ChartNoteUnit:
            # 如果这个音符已经被作为某个链的一部分处理过了，则跳过
            if note.Uid in processed_note_ids:
                continue

            # 我们只关心Hold类型的音符，并且需要找到链的起始点
            # 链的起始点是 prev_note 为 None 的 Hold 音符
            if NoteTypes(note.Type) == NoteTypes.Hold and note.prev_note is None:
                # 找到了一个Hold链的起始点
                # 判断是否为单段长条，单段不需要重切holds
                if note.next_note is None:
                    merged_notes.append(note)
                    processed_note_ids.add(note.Uid)  # 标记为已处理 (以防后续处理到)
                    continue

                current_chain_notes: list[Note] = []
                chain_start_note = note
                chain_end_note = note

                # 遍历整个链条，收集所有组成音符
                temp_note = chain_start_note
                while temp_note is not None and NoteTypes(note.Type) == NoteTypes.Hold:
                    current_chain_notes.append(temp_note)
                    processed_note_ids.add(temp_note.Uid)  # 标记为已处理
                    chain_end_note = temp_note  # 更新链的结束音符
                    temp_note = temp_note.next_note

                # 至此，current_chain_notes 包含了从 chain_start_note 到 chain_end_note 的所有Hold音符

                # 创建新的合并后的Hold音符
                # 新音符的just是链条起始音符的just
                merged_just = chain_start_note.just
                # 新音符的最终结束时间是链条结束音符的最后一个holds时间点
                merged_end_time = chain_end_note.holds[-1]
                # 新音符的起始位置是链条起始音符的起始位置
                merged_start_pos = chain_start_note.StartPos
                # 新音符的结束位置是链条结束音符的结束位置
                merged_end_pos = chain_end_note.EndPos

                # 使用 GetHolds 函数计算新的holds时间点
                # 单段长条不需要重新计算，直接采用原始数据避免累积误差
                # 多段从重新计算改成筛掉小于半拍的间隔？

                new_holds = self._GetHolds_multi_bpm(merged_just, merged_end_time)

                # 创建新的合并音符对象
                # 使用第一个音符的UID

                merged_note = Note(
                    **
                    {"just": merged_just,
                     "holds": new_holds,
                     "Uid": chain_start_note.Uid,
                     "Flags": self._generate_flags(1, merged_start_pos, merged_end_pos),
                     }
                )
                merged_notes.append(merged_note)

            # 如果不是Hold类型，或者不是链的起始点 (即prev_note不为None的Hold音符会被链头处理)，
            # 直接添加到结果列表（如果未处理过）
            elif note.Uid not in processed_note_ids:
                merged_notes.append(note)
                processed_note_ids.add(note.Uid)  # 标记为已处理 (以防后续处理到)

        # 排序最终的音符列表，通常按时间排序
        merged_notes.sort(key=lambda note: float(note.just))
        self.ChartNoteUnit = merged_notes


if __name__ == "__main__":
    musicdb = MusicDB()

    c = Chart(musicdb, "105101", "03")
    logger.debug(c.AllNoteSize)
    # logger.debug(c.ChartEvents)
    logger.debug(c.bpm)
    for music in musicdb.db:
        # logger.debug(music)
        break

    import os
    files = os.listdir(os.path.join("Data", "bytes"))
    # logger.debug(files)
    bytes = set()
    for file in files:
        if file.endswith(".bytes"):
            bytes.add(file.split("_")[-2])

    f = open("log.txt", "w", encoding="UTF-8")
    for music in sorted(bytes):
        for difficulty in ["01", "02", "03", "04"]:
            c = Chart(musicdb, str(music), difficulty)
            i_feverstart = 0
            i_feverend = 0
            for index, event in enumerate(c.ChartEvents):
                if event[1] == "FeverStart":
                    i_feverstart = index
                elif event[1] == "FeverEnd":
                    i_feverend = index
                    break
            fevernotes = i_feverend - i_feverstart - 1
            feverrate = fevernotes * 100 / c.AllNoteSize
            f.write(f"{music}\t{c.music.Title}\t{difficulty}\t{fevernotes}\t{c.AllNoteSize}\t{feverrate:.2f}%\n")
            # logger.debug(f"难度 {difficulty}: {fevernotes} / {c.AllNoteSize} ({feverrate:.2f}%)")
    f.close()
