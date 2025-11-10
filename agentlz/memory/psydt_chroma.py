import os
import json
from hashlib import sha256
from typing import Any, Dict, List

from agentlz.core.logger import setup_logging
from agentlz.config.settings import get_settings
from agentlz.core.model_factory import get_hf_embeddings

try:
    from langchain_community.vectorstores import Chroma
except Exception:  # 兼容旧版本
    from langchain.vectorstores import Chroma  # type: ignore


def _concat_dialog(sample: Dict[str, Any]) -> str:
    """
    将样本中的多轮对话拼接为纯文本。

    针对常见字段结构进行鲁棒处理：
    - conversations/messages/history/dialogue/dialog/utterances
    - 若为 dict，尝试使用 role/speaker/from 与 content/text/utterance/value
    - 若不存在上述结构，则回退拼接 instruction/input/output/response 等字段
    """
    seq_keys = [
        "conversations",
        "messages",
        "history",
        "dialogue",
        "dialog",
        "utterances",
    ]
    for k in seq_keys:
        if k in sample and isinstance(sample[k], list):
            lines: List[str] = []
            for turn in sample[k]:
                if isinstance(turn, str):
                    lines.append(turn.strip())
                elif isinstance(turn, dict):
                    role = turn.get("role") or turn.get("speaker") or turn.get("from") or turn.get("author")
                    content = turn.get("content") or turn.get("text") or turn.get("utterance") or turn.get("value")
                    if role and content:
                        lines.append(f"{role}: {str(content).strip()}")
                    elif content:
                        lines.append(str(content).strip())
                    else:
                        lines.append(json.dumps(turn, ensure_ascii=False))
                else:
                    lines.append(str(turn))
            return "\n".join(lines)

    # 回退：拼接可能出现的单字段
    fallback_keys = [
        "instruction",
        "input",
        "question",
        "prompt",
        "output",
        "response",
        "answer",
    ]
    parts: List[str] = []
    for k in fallback_keys:
        v = sample.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(f"{k}: {v.strip()}")
    if parts:
        return "\n".join(parts)

    # 最终兜底：序列化为 JSON 文本
    return json.dumps(sample, ensure_ascii=False)


def persist_psydt_to_chroma(persist_dir: str) -> None:
    """
    将 ModelScope 数据集 YIRONGCHEN/PsyDTCorpus/train 的多轮对话拼接为文本，
    使用本地 HuggingFace 中文句向量模型进行向量化，并持久化到指定目录的 Chroma 向量库。

    要点：
    - 流式迭代样本，批量入库，避免一次性加载至内存（内存安全）。
    - 不写入任何原始样本数据到磁盘，仅持久化向量与元数据（不落盘原始数据）。
    - 通过确定性 ID 跳过已存在记录，保证可重复执行（幂等）。

    参数:
        persist_dir: Chroma 持久化目录路径。

    返回:
        None
    """
    settings = get_settings()
    logger = setup_logging(settings.log_level)

    try:
        from modelscope.msdatasets import MsDataset  # 延迟导入，减少无关环境依赖
    except Exception as e:
        raise RuntimeError(
            "缺少 modelscope 依赖，请先安装: pip install modelscope"
        ) from e

    # 1) Embeddings（允许通过环境变量 HF_EMBEDDING_MODEL 指定本地/自定义模型路径）
    embeddings = get_hf_embeddings(
        model_name=os.getenv("HF_EMBEDDING_MODEL"),
        device=os.getenv("HF_EMBEDDING_DEVICE") or None,
        normalize_embeddings=True,
    )

    # 2) 初始化 Chroma（LangChain 兼容向量库封装）
    collection_name = os.getenv("CHROMA_COLLECTION") or "psydt_train"
    vectorstore = Chroma(
        collection_name=collection_name,
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )

    # 3) 流式加载 ModelScope 数据集
    ds = MsDataset.load("YIRONGCHEN/PsyDTCorpus", split="train")

    batch_size = 64
    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []
    total = 0
    skipped = 0

    for sample in ds:  # MsDataset 是可迭代对象
        text = _concat_dialog(sample)

        # 生成确定性 ID（优先使用样本自带 id/uid/sid，否则使用内容哈希）
        raw_id = sample.get("id") or sample.get("uid") or sample.get("sid")
        if raw_id is None:
            h = sha256(text.encode("utf-8")).hexdigest()[:32]
            doc_id = f"psydt-train-{h}"
        else:
            doc_id = f"psydt-train-{raw_id}"

        # 重复检测（若集合已存在该 ID，则跳过）
        try:
            existing = getattr(vectorstore, "_collection", None)
            if existing is not None:
                got = existing.get(ids=[doc_id])
                if got and got.get("ids"):
                    skipped += 1
                    continue
        except Exception:
            # 容忍私有属性或驱动实现差异
            pass

        meta = {
            "dataset": "YIRONGCHEN/PsyDTCorpus",
            "split": "train",
            "source": "ModelScope",
        }

        texts.append(text)
        metadatas.append(meta)
        ids.append(doc_id)

        if len(texts) >= batch_size:
            vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            vectorstore.persist()  # 及时落盘向量，保证可重复执行与恢复
            total += len(texts)
            texts.clear()
            metadatas.clear()
            ids.clear()

    # 收尾批次
    if texts:
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        vectorstore.persist()
        total += len(texts)

    logger.info(
        f"PsyDTCorpus(train) 已写入向量: {total} 条，重复跳过: {skipped} 条，目录: {persist_dir}"
    )