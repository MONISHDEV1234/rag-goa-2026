import faiss, json

index = faiss.read_index("data/index_minilm/faiss.index")
with open("data/index_minilm/model_info.json") as f:
    info = json.load(f)

print(f"Index vectors : {index.ntotal}")
print(f"Index dim     : {index.d}")
print(f"Model         : {info['model_name']}")
print(f"Is E5         : {info['is_e5']}")
print("STATUS: faiss.index is valid and loadable!")
