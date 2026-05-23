# -*- coding: utf-8 -*-
import json

log_path = r"C:\Users\TQT\.gemini\antigravity\brain\facaca67-1b9f-460d-9205-2bab7233ebb7\.system_generated\logs\transcript.jsonl"
with open(log_path, "r") as f:
    for line in f:
        # Check if line contains 'USER_INPUT' and '表格' (UTF-8 encoded string)
        if "USER_INPUT" in line and "\xe8\xa1\xa8\xe6\xa0\xbc" in line:
            try:
                data = json.loads(line)
                print("STEP INDEX: {}".format(data.get("step_index")))
                print("CONTENT:")
                print(data.get("content").encode("utf-8") if isinstance(data.get("content"), unicode) else data.get("content"))
                print("-" * 50)
            except Exception as e:
                pass
