import json
import os
from typing import TypedDict, List

class Track(TypedDict):
    title: str
    bvid: str

input_dir = "my-bilibili"
output_file = "bilibili-tracks.json"

all_tracks: List[Track] = []

# 获取所有 .json 文件并按文件名排序
json_files = sorted([
    f for f in os.listdir(input_dir)
    if f.endswith(".json")
])

for filename in json_files:
    file_path = os.path.join(input_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            medias = data.get("data", {}).get("medias", [])
            for item in medias:
                if "title" in item and "bvid" in item:
                    all_tracks.append(Track(
                        title=item["title"],
                        bvid=item["bvid"]
                    ))
    except (json.JSONDecodeError, OSError) as e:
        print(f"错误处理文件 {filename}: {e}")

# 写入最终结果
with open(output_file, "w", encoding="utf-8") as out_f:
    json.dump(all_tracks, out_f, ensure_ascii=False, indent=2)

print(f"共提取 {len(all_tracks)} 条 Track，已保存到 {output_file}")
