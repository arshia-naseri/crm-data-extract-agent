import os
import math

CLIENT_DIR = "client_info"
BATCH_DIR = "batch"
BATCH_SIZE = 25

folders = sorted(os.listdir(CLIENT_DIR))
folders = [f for f in folders if os.path.isdir(os.path.join(CLIENT_DIR, f))]

os.makedirs(BATCH_DIR, exist_ok=True)

total_batches = math.ceil(len(folders) / BATCH_SIZE)

for i in range(total_batches):
    chunk = folders[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
    path = os.path.join(BATCH_DIR, f"batch_{i + 1}.md")
    with open(path, "w") as f:
        f.write("\n".join(chunk) + "\n")

print(f"{len(folders)} folders → {total_batches} batches of {BATCH_SIZE} in {BATCH_DIR}/")
