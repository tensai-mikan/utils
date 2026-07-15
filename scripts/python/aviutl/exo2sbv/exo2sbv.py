from datetime import datetime
import os
import re
import pprint


def decode_exo_text(hex_str: str) -> str:
    if not hex_str:
        return ""
    try:
        # 1. 16進数文字列をバイナリに変換
        binary_data = bytes.fromhex(hex_str)
        # 2. UTF-16LEでデコードし、右側のヌル文字（0埋め）を削除
        decoded_text = binary_data.decode('utf-16le').rstrip('\x00')
        
        # 3. Windowsの改行(\r\n)および通常の改行(\n)を完全に消去
        cleaned_text = decoded_text.replace('\r\n', '').replace('\n', '').replace('\r', '')
        
        return cleaned_text
    except Exception as e:
        return f"[Decode Error: {e}]"
    


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

exo_file = input("exo: ")
output = input("output: ")

# 全体設定とオブジェクト格納用
exedit_info = {}
objects = {}

section_re = re.compile(r'^\[(.*)\]$')
current_section = None

# 1. ファイルを読み込んで辞書に整理
with open(exo_file, "r", encoding="cp932") as f:
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
            
            # 全体設定の保存
            if current_section == "exedit":
                exedit_info[key] = value
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
rate = exedit_info.get("rate", 1)
scale = exedit_info.get("scale", 1)
fps = rate / scale

# 3. _name=テキスト のオブジェクトだけを抽出
text_objects = []
for obj_id in sorted(objects.keys()):
    obj = objects[obj_id]
    
    # サブセクション「0」の _name が「テキスト」のものを抽出
    if obj["sub_sections"].get("0", {}).get("_name") == "テキスト":
        obj["sub_sections"]["0"]["text"] = decode_exo_text(obj["sub_sections"]["0"]["text"])
        text_objects.append(obj)

#出力

try:
    with open(output, "w", encoding="utf-8") as out_f:
        for i, obj in enumerate(text_objects):
            start_frame = obj.get("start", 1)
            end_frame = obj.get("end", 1)
            
            text_content = obj["sub_sections"]["0"].get("text", "")
            
            # 空の字幕オブジェクトはスキップ
            if not text_content:
                continue
                
            # 時間の計算と整形
            start_time_str = format_sbv_time(start_frame, fps)
            end_time_str = format_sbv_time(end_frame+1, fps)
            
            # sbvのフォーマットで書き込み
            out_f.write(f"{start_time_str},{end_time_str}\n")
            out_f.write(f"{text_content}\n")
            
            # 最後の行以外には、字幕間の区切りとして空行を1つ入れる
            if i < len(text_objects) - 1:
                out_f.write("\n")
                
    print(f"\n[成功] sbvファイルを出力しました: {output}")

except Exception as e:
    print(f"\n[エラー] sbvファイルの書き出しに失敗しました: {e}")
