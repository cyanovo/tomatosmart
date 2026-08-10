"""
番茄溯源区块链 —— 区块链保证溯源数据不可篡改
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List

# Docker 卷路径：/app/saves 对应 docker/volumes/greenhouse
_SAVES_DIR = Path("/app/saves") if Path("/app/saves").exists() else Path(__file__).resolve().parent.parent.parent.parent / "docker" / "volumes" / "greenhouse"
_SAVES_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _SAVES_DIR / ".tomato_blockchain.json"

_state: Dict[str, Any] = {"chain": []}


def _load():
    global _state
    if DB_PATH.exists():
        try:
            _state = json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            _state = {"chain": []}


def _save():
    DB_PATH.write_text(
        json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _hash(record: Dict[str, Any]) -> str:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def calculate_hash(block: Dict[str, Any]) -> str:
    return _hash({
        "index": block["index"],
        "timestamp": block["timestamp"],
        "data": block["data"],
        "previous_hash": block["previous_hash"],
        "nonce": block["nonce"],
    })


def proof_of_work(block_data: Dict[str, Any], difficulty: int = 4) -> tuple:
    """工作量证明：前 difficulty 位为 0"""
    prefix = "0" * difficulty
    nonce = 0
    while True:
        block_data["nonce"] = nonce
        h = calculate_hash(block_data)
        if h.startswith(prefix):
            return h, nonce
        nonce += 1


def create_genesis_block() -> Dict[str, Any]:
    block = {
        "index": 0,
        "timestamp": time.time(),
        "data": {"event": "创世区块 - 番茄溯源链", "record_id": "GENESIS"},
        "previous_hash": "0" * 64,
        "nonce": 0,
    }
    h, nonce = proof_of_work(block)
    block["hash"] = h
    block["nonce"] = nonce
    return block


def add_block(data: Dict[str, Any]) -> Dict[str, Any]:
    """将番茄溯源数据写入区块链"""
    _load()
    chain = _state.get("chain", [])
    if not chain:
        chain = [create_genesis_block()]

    prev = chain[-1]
    block = {
        "index": prev["index"] + 1,
        "timestamp": time.time(),
        "data": data,
        "previous_hash": prev["hash"],
        "nonce": 0,
    }
    h, nonce = proof_of_work(block)
    block["hash"] = h
    block["nonce"] = nonce
    chain.append(block)
    _state["chain"] = chain
    _save()
    return block


def get_chain() -> List[Dict[str, Any]]:
    _load()
    chain = _state.get("chain", [])
    if not chain:
        return []
    return [
        {
            "index": b["index"],
            "timestamp": b["timestamp"],
            "data": b["data"],
            "previous_hash": b["previous_hash"],
            "hash": b["hash"],
            "nonce": b["nonce"],
        }
        for b in chain
    ]


def verify_chain() -> Dict[str, Any]:
    """验证区块链完整性"""
    _load()
    chain = _state.get("chain", [])
    if not chain:
        return {"valid": True, "details": [], "message": "链为空"}

    details = []
    all_valid = True
    for i in range(len(chain)):
        block = chain[i]
        recalc = calculate_hash(block)
        hash_ok = recalc == block["hash"]
        prev_ok = True
        if i > 0:
            prev_ok = block["previous_hash"] == chain[i - 1]["hash"]

        if not hash_ok or not prev_ok:
            all_valid = False
        details.append({
            "index": block["index"],
            "hash_match": hash_ok,
            "prev_match": prev_ok,
            "stored_hash": block["hash"][:24] + "...",
            "recalculated_hash": recalc[:24] + "...",
        })

    return {
        "valid": all_valid,
        "details": details,
        "message": "所有区块哈希一致，链完整 ✓" if all_valid else "发现哈希不匹配！数据可能已被篡改！",
    }


def get_block_count() -> int:
    _load()
    return len(_state.get("chain", []))


def reset_chain():
    global _state
    _state = {"chain": []}
    if DB_PATH.exists():
        DB_PATH.unlink()


# 启动时加载
_load()

