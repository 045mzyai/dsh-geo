"""GEO基准测试Agent — 蒸馏自GEO-optim/GEO (Princeton, arXiv:2311.09735)

7维评估体系 + 引用印象评分算法

7个评估维度(1-5分):
  - relevance: 引用与查询的相关性
  - influence: 引用对答案完整性的贡献
  - diversity: 引用中观点的多样性
  - uniqueness: 引用提供信息的独特性
  - follow: 引用引导后续行动的能力
  - subjpos: 引用在答案中的位置
  - subjcount: 引用被提及的次数

3种印象评分算法:
  - wordpos: 词数×位置衰减(越靠前权重越高)
  - word: 纯词数统计
  - pos: 位置加权计数
"""

import json
import math
import re
import logging
import threading
import uuid
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

# 异步任务存储 — 用类封装避免模块级变量问题
class _TaskStore:
    _instance = None
    _tasks = {}

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set(self, task_id, data):
        self._tasks[task_id] = data

    def get_task(self, task_id):
        return self._tasks.get(task_id)

    def keys(self):
        return list(self._tasks.keys())

MODEL_TEMPS = {"kimi-k3": 1.0}

# ── 7维评估prompt模板 (蒸馏自geval_prompts/) ──

EVAL_DIMENSIONS = {
    "relevance": "引用文本与用户查询的直接相关程度。评估引用是否完整、精确、清晰地回答了用户问题。",
    "influence": "引用对答案完整性、连贯性和整体质量的贡献程度。该来源是否不可或缺？",
    "diversity": "引用中涵盖的观点或主题的广度。该来源是否为答案带来了独特的视角？",
    "uniqueness": "引用提供的信息在其他来源中找不到的程度。该来源是否提供了独家信息？",
    "follow": "引用内容引导用户进行后续行动的能力。是否包含明确的行动建议？",
}

EVAL_PROMPT_TEMPLATE = """你是一个GEO（生成式引擎优化）评估专家。请评估以下AI回答中目标公司被引用的质量。

用户查询：{query}
目标公司：{company_name}
AI回答：
{answer}

请从以下5个维度评分（1-5分，1=最差，5=最优）：

1. 相关性(Relevance)：{relevance_desc}
2. 影响力(Influence)：{influence_desc}
3. 多样性(Diversity)：{diversity_desc}
4. 独特性(Uniqueness)：{uniqueness_desc}
5. 引导力(Follow)：{follow_desc}

同时判断：
- mention_position: 目标公司在回答中的位置(first/middle/last/none)
- mention_count: 被提及的次数(整数)

返回JSON：
{{
  "relevance": 1-5,
  "influence": 1-5,
  "diversity": 1-5,
  "uniqueness": 1-5,
  "follow": 1-5,
  "mention_position": "first/middle/last/none",
  "mention_count": 0
}}"""


def _call_llm(prompt: str, model: str = None, temperature: float = None, json_mode: bool = False) -> str:
    model = model or DEFAULT_MODEL
    temp = temperature if temperature is not None else MODEL_TEMPS.get(model, 0.3)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── 引用印象评分算法 (蒸馏自utils.py) ──

def extract_citations(text: str) -> list:
    """从AI回答中提取引用标记，返回[[words, sentence, citations], ...]"""
    citation_pattern = r'\[[^\w\s]*\d+[^\w\s]*\]'
    sentences = re.split(r'[。！？\n]', text)
    result = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        citations = [int(x) for x in re.findall(r'\d+', ''.join(re.findall(citation_pattern, sent)))]
        words = [w for w in re.split(r'\s+', sent) if len(w) > 2]
        result.append({"words": words, "sentence": sent, "citations": citations})
    return result


def impression_wordpos(sentences: list, n: int = 5) -> list:
    """词数×位置衰减评分 — 越靠前的引用权重越高"""
    scores = [0.0] * n
    total_sents = len(sentences)
    for i, sent in enumerate(sentences):
        word_count = len(sent["words"])
        for cit in sent["citations"]:
            score = word_count
            if total_sents > 1:
                score *= math.exp(-1 * i / (total_sents - 1))
            score /= max(len(sent["citations"]), 1)
            if 1 <= cit <= n:
                scores[cit - 1] += score
    total = sum(scores)
    if total > 0:
        return [s / total for s in scores]
    return [1.0 / n] * n


def impression_word_count(sentences: list, n: int = 5) -> list:
    """纯词数评分"""
    scores = [0.0] * n
    for sent in sentences:
        word_count = len(sent["words"])
        for cit in sent["citations"]:
            score = word_count / max(len(sent["citations"]), 1)
            if 1 <= cit <= n:
                scores[cit - 1] += score
    total = sum(scores)
    if total > 0:
        return [s / total for s in scores]
    return [1.0 / n] * n


def impression_position(sentences: list, n: int = 5) -> list:
    """位置加权评分"""
    scores = [0.0] * n
    total_sents = len(sentences)
    for i, sent in enumerate(sentences):
        for cit in sent["citations"]:
            score = 1.0
            if total_sents > 1:
                score *= math.exp(-1 * i / (total_sents - 1))
            score /= max(len(sent["citations"]), 1)
            if 1 <= cit <= n:
                scores[cit - 1] += score
    total = sum(scores)
    if total > 0:
        return [s / total for s in scores]
    return [1.0 / n] * n


# ── GEO基准测试主函数 ──

def run_benchmark(company_name: str, industry: str = "", queries: list = None, models: list = None) -> dict:
    """对目标公司执行完整GEO基准测试

    流程(蒸馏自run_geo.py improve函数):
    1. 对每个查询×每个模型生成AI回答
    2. 提取引用并计算印象评分(wordpos/word/pos)
    3. 对每个回答执行7维评估
    4. 汇总基准分数
    """
    if queries is None:
        queries = [
            f"请推荐一家{industry}公司" if industry else f"{company_name}怎么样",
            f"{company_name}怎么样",
            f"{industry}哪家公司服务好" if industry else f"推荐{company_name}",
        ]
    if models is None:
        models = ["deepseek-v4-pro", "kimi-k3", "glm-5.2"]

    all_results = []
    total_mentions = 0
    total_queries = 0
    eval_scores_sum = {"relevance": 0, "influence": 0, "diversity": 0, "uniqueness": 0, "follow": 0}
    eval_count = 0
    impression_scores_all = []

    for model_name in models:
        for query in queries:
            total_queries += 1
            try:
                # 生成AI回答
                answer = _call_llm(query, model=model_name, temperature=MODEL_TEMPS.get(model_name, 0.5))

                # 提取引用
                citations = extract_citations(answer)

                # 印象评分
                wordpos_scores = impression_wordpos(citations, n=5)
                word_scores = impression_word_count(citations, n=5)
                pos_scores = impression_position(citations, n=5)
                impression_scores_all.append(wordpos_scores)

                # 7维评估
                eval_prompt = EVAL_PROMPT_TEMPLATE.format(
                    query=query,
                    company_name=company_name,
                    answer=answer[:2000],
                    relevance_desc=EVAL_DIMENSIONS["relevance"],
                    influence_desc=EVAL_DIMENSIONS["influence"],
                    diversity_desc=EVAL_DIMENSIONS["diversity"],
                    uniqueness_desc=EVAL_DIMENSIONS["uniqueness"],
                    follow_desc=EVAL_DIMENSIONS["follow"],
                )
                try:
                    eval_raw = _call_llm(eval_prompt, temperature=0.3, json_mode=True)
                    eval_result = json.loads(eval_raw)
                except Exception:
                    eval_result = {"relevance": 0, "influence": 0, "diversity": 0, "uniqueness": 0, "follow": 0,
                                   "mention_position": "none", "mention_count": 0}

                mentioned = eval_result.get("mention_count", 0) > 0
                if mentioned:
                    total_mentions += 1
                    for k in eval_scores_sum:
                        eval_scores_sum[k] += eval_result.get(k, 0)
                    eval_count += 1

                all_results.append({
                    "model": model_name,
                    "query": query,
                    "answer_length": len(answer),
                    "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
                    "citations_found": len(citations),
                    "impression_wordpos": [round(s, 4) for s in wordpos_scores],
                    "impression_word": [round(s, 4) for s in word_scores],
                    "impression_pos": [round(s, 4) for s in pos_scores],
                    "eval_scores": {k: eval_result.get(k, 0) for k in EVAL_DIMENSIONS},
                    "mention_position": eval_result.get("mention_position", "none"),
                    "mention_count": eval_result.get("mention_count", 0),
                })
            except Exception as e:
                logger.warning("基准测试查询失败 model=%s query=%s: %s", model_name, query[:30], e)
                all_results.append({"model": model_name, "query": query, "error": str(e)})

    # 汇总
    display_rate = round(total_mentions / total_queries, 4) if total_queries > 0 else 0
    avg_eval = {k: round(v / eval_count, 2) for k, v in eval_scores_sum.items()} if eval_count > 0 else eval_scores_sum

    # 综合GEO基准分(0-100)
    geo_score = 0
    if eval_count > 0:
        eval_avg = sum(avg_eval.values()) / len(avg_eval)
        geo_score = round((display_rate * 0.4 + (eval_avg / 5) * 0.6) * 100, 1)

    return {
        "company_name": company_name,
        "total_queries": total_queries,
        "total_mentions": total_mentions,
        "display_rate": display_rate,
        "geo_benchmark_score": geo_score,
        "avg_eval_scores": avg_eval,
        "results": all_results,
    }


def start_benchmark_async(company_name: str, industry: str = "", queries: list = None, models: list = None) -> str:
    """启动异步基准测试，返回task_id"""
    task_id = str(uuid.uuid4())[:8]
    store = _TaskStore.get()
    store.set(task_id, {
        "status": "running",
        "progress": 0,
        "total_steps": 0,
        "current_step": 0,
        "current_desc": "",
        "result": None,
        "error": None,
    })

    total_queries = len(queries) if queries else 3
    total_models = len(models) if models else 3
    total_steps = total_queries * total_models * 2
    store.get_task(task_id)["total_steps"] = total_steps

    def _worker():
        try:
            result = _run_benchmark_with_progress(
                task_id, company_name, industry, queries, models
            )
            store.get_task(task_id)["result"] = result
            store.get_task(task_id)["status"] = "done"
            store.get_task(task_id)["progress"] = 100
        except Exception as e:
            logger.error("异步基准测试失败: %s", e, exc_info=True)
            store.get_task(task_id)["error"] = str(e)
            store.get_task(task_id)["status"] = "failed"

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return task_id


def _run_benchmark_with_progress(task_id: str, company_name: str, industry: str,
                                  queries: list, models: list, tasks: dict = None) -> dict:
    """带进度追踪的基准测试

    Args:
        tasks: 外部任务存储dict，None=使用_TaskStore
    """
    if tasks is None:
        store = _TaskStore.get()
        def _update(key, val):
            store.get_task(task_id)[key] = val
        def _get(key):
            return store.get_task(task_id).get(key)
    else:
        def _update(key, val):
            tasks[task_id][key] = val
        def _get(key):
            return tasks[task_id].get(key)

    if queries is None:
        queries = [
            f"请推荐一家{industry}公司" if industry else f"{company_name}怎么样",
            f"{company_name}怎么样",
            f"{industry}哪家公司服务好" if industry else f"推荐{company_name}",
        ]
    if models is None:
        models = ["deepseek-v4-pro", "kimi-k3", "glm-5.2"]

    all_results = []
    total_mentions = 0
    total_queries = 0
    eval_scores_sum = {"relevance": 0, "influence": 0, "diversity": 0, "uniqueness": 0, "follow": 0}
    eval_count = 0
    step = 0

    for model_name in models:
        for query in queries:
            total_queries += 1
            step += 1
            _update("current_step", step)
            _update("current_desc", f"{model_name}: {query[:30]}")
            _update("progress", int(step / _get("total_steps") * 90))

            try:
                answer = _call_llm(query, model=model_name, temperature=MODEL_TEMPS.get(model_name, 0.5))
                step += 1
                _update("current_step", step)
                _update("current_desc", f"评估: {model_name} 回答")
                _update("progress", int(step / _get("total_steps") * 90))

                citations = extract_citations(answer)
                wordpos_scores = impression_wordpos(citations, n=5)
                word_scores = impression_word_count(citations, n=5)
                pos_scores = impression_position(citations, n=5)

                eval_prompt = EVAL_PROMPT_TEMPLATE.format(
                    query=query, company_name=company_name, answer=answer[:2000],
                    relevance_desc=EVAL_DIMENSIONS["relevance"], influence_desc=EVAL_DIMENSIONS["influence"],
                    diversity_desc=EVAL_DIMENSIONS["diversity"], uniqueness_desc=EVAL_DIMENSIONS["uniqueness"],
                    follow_desc=EVAL_DIMENSIONS["follow"],
                )
                try:
                    eval_raw = _call_llm(eval_prompt, temperature=0.3, json_mode=True)
                    eval_result = json.loads(eval_raw)
                except Exception:
                    eval_result = {"relevance": 0, "influence": 0, "diversity": 0, "uniqueness": 0, "follow": 0,
                                   "mention_position": "none", "mention_count": 0}

                mentioned = eval_result.get("mention_count", 0) > 0
                if mentioned:
                    total_mentions += 1
                    for k in eval_scores_sum:
                        eval_scores_sum[k] += eval_result.get(k, 0)
                    eval_count += 1

                all_results.append({
                    "model": model_name, "query": query,
                    "answer_length": len(answer),
                    "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
                    "citations_found": len(citations),
                    "impression_wordpos": [round(s, 4) for s in wordpos_scores],
                    "impression_word": [round(s, 4) for s in word_scores],
                    "impression_pos": [round(s, 4) for s in pos_scores],
                    "eval_scores": {k: eval_result.get(k, 0) for k in EVAL_DIMENSIONS},
                    "mention_position": eval_result.get("mention_position", "none"),
                    "mention_count": eval_result.get("mention_count", 0),
                })
            except Exception as e:
                logger.warning("基准测试查询失败 model=%s query=%s: %s", model_name, query[:30], e)
                all_results.append({"model": model_name, "query": query, "error": str(e)})

    display_rate = round(total_mentions / total_queries, 4) if total_queries > 0 else 0
    avg_eval = {k: round(v / eval_count, 2) for k, v in eval_scores_sum.items()} if eval_count > 0 else eval_scores_sum
    geo_score = 0
    if eval_count > 0:
        eval_avg = sum(avg_eval.values()) / len(avg_eval)
        geo_score = round((display_rate * 0.4 + (eval_avg / 5) * 0.6) * 100, 1)

    return {
        "company_name": company_name, "total_queries": total_queries,
        "total_mentions": total_mentions, "display_rate": display_rate,
        "geo_benchmark_score": geo_score, "avg_eval_scores": avg_eval,
        "results": all_results,
    }


def get_benchmark_status(task_id: str) -> dict:
    """查询异步基准测试状态"""
    store = _TaskStore.get()
    task = store.get_task(task_id)
    if not task:
        return {"error": "任务不存在"}
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "current_step": task["current_step"],
        "total_steps": task["total_steps"],
        "current_desc": task["current_desc"],
        "result": task["result"],
        "error": task["error"],
    }
