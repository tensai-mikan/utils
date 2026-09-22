import re


def format_sbv_time(frame: int, fps: float) -> str:
    """フレーム数をsbv形式の時間フォーマット (h:mm:ss.fff) に変換する"""
    # 仕様：0秒目を1フレームとするため、計算前に-1する
    total_seconds = (frame - 1) / fps
    
    # 負の数になってしまった場合の安全弁
    if total_seconds < 0:
        total_seconds = 0.0
        
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int(round((total_seconds % 1) * 1000))
    
    # ミリ秒が1000になってしまった場合の繰り上げ処理
    if milliseconds == 1000:
        milliseconds = 0
        seconds += 1
        if seconds == 60:
            seconds = 0
            minutes += 1
            if minutes == 60:
                minutes = 0
                hours += 1

    return f"{hours}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

# ---------------------------

aup2_file = input("aup2: ")
output = input("output: ")

# 全体設定とオブジェクト格納用
scene_info = {}
objects = {}

section_re = re.compile(r'^\[(.*)\]$')
current_section = None

# 1. ファイルを読み込んで辞書に整理
with open(aup2_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        match = section_re.match(line)
        if match:
            current_section = match.group(1)
            if current_section.isdigit():
                obj_id = int(current_section)
                objects[obj_id] = {"sub_sections": {}}
            continue
            
        if "=" in line and current_section is not None:
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            
            # 数値変換
            if value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass
            
            # aup2のシーン設定を保存
            if current_section == "scene.0":
                scene_info[key] = value
            # 各オブジェクトの基本情報
            elif current_section.isdigit():
                obj_id = int(current_section)
                objects[obj_id][key] = value
            # サブセクション（[0.0] など）の情報
            elif "." in current_section:
                main_part, sub_part = current_section.split(".", 1)
                if main_part.isdigit():
                    obj_id = int(main_part)
                    if obj_id in objects:
                        if sub_part not in objects[obj_id]["sub_sections"]:
                            objects[obj_id]["sub_sections"][sub_part] = {}
                        objects[obj_id]["sub_sections"][sub_part][key] = value

# 2. 必須の全体設定・FPSの計算
rate = scene_info.get("video.rate", 1)
scale = scene_info.get("video.scale", 1)
fps = rate / scale

# 3. effect.name=テキスト のオブジェクトだけを抽出
text_objects = []
for obj_id in sorted(objects.keys()):
    obj = objects[obj_id]
    
    text_section = obj["sub_sections"].get("0", {})
    if text_section.get("effect.name") == "テキスト":
        obj["text"] = text_section.get("テキスト", "").replace(r"\n", "\n")
        if obj["text"]:
            text_objects.append(obj)

text_objects.sort(key=lambda obj: int(str(obj.get("frame", "0")).split(",")[0]))

#出力

try:
    with open(output, "w", encoding="utf-8") as out_f:
        written_count = 0
        for obj in text_objects:
            frame_values = [int(value) for value in str(obj.get("frame", "0,0")).split(",")]
            start_frame = frame_values[0]
            end_frame = frame_values[-1]
            
            text_content = obj.get("text", "")
            
            # 時間の計算と整形
            start_time_str = format_sbv_time(start_frame, fps)
            end_time_str = format_sbv_time(end_frame+1, fps)
            
            # sbvのフォーマットで書き込み
            out_f.write(f"{start_time_str},{end_time_str}\n")
            out_f.write(f"{text_content}\n")
            
            written_count += 1
            if written_count < len(text_objects):
                out_f.write("\n")
                
    print(f"\n[成功] sbvファイルを出力しました: {output}")

except Exception as e:
    print(f"\n[エラー] sbvファイルの書き出しに失敗しました: {e}")
