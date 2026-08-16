"""AI监控Agent - 通过MzyToken多模型查询品牌在AI引擎中的引用情况

设计要点：
- 5个模型 ThreadPoolExecutor 并行（原串行20次调用40-100s → 并行后约1/5）
- 支持异步任务模式（start_monitor_async + get_monitor_status），前端轮询进度
- 数据契约与前端一致：overall.avg_accuracy/negative_rate、platform.accuracy/note 均真实计算
- 查询集与品牌词从公司参数推导，不硬编码演示数据
"""
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

# 每个模型对应一个"AI引擎"视角，使用MzyToken实际可用模型
TEST_MODELS = {
    "deepseek-v4-pro": {"label": "DeepSeek V4 Pro", "icon": "deepseek"},
    "kimi-k3": {"label": "Kimi K3", "icon": "kimi"},
    "glm-5.2": {"label": "智谱 GLM-5.2", "icon": "glm"},
    "minimax-m3": {"label": "MiniMax M3", "icon": "minimax"},
    "hy3": {"label": "混元 H3", "icon": "hunyuan"},
}

# 某些模型要求特定temperature
MODEL_TEMPS = {"kimi-k3": 1.0}

# 准确度等级 → 百分制映射（用于avg_accuracy聚合）
ACCURACY_SCORE = {"高": 100, "中": 70, "低": 40, "无": 0}

# 负面提及检测词表（品牌出现且同段落出现这些词 → 计为负面提及）
NEGATIVE_KEYWORDS = [
    "投诉", "欺诈", "诈骗", "跑路", "差评", "骗局", "维权", "不靠谱",
    "不可靠", "风险", "纠纷", "违规", "处罚", "失信", "拖欠", "退款难",
]

# 公司名后缀，用于推导简称
COMPANY_SUFFIXES = ["股份有限公司", "有限责任公司", "有限公司", "科技", "有限", "公司"]

_MONITOR_TASKS = {}
_TASKS_LOCK = threading.Lock()


def derive_company_parts(company: str, extra_keywords: list = None) -> list:
    """从公司全称推导品牌匹配词（全称+逐级去后缀简称+用户补充品牌词）"""
    parts = [company]
    short = company
    for suffix in COMPANY_SUFFIXES:
        short = short.replace(suffix, "")
    short = short.strip()
    if short and short != company:
        parts.append(short)
    if extra_keywords:
        for kw in extra_keywords:
            kw = kw.strip()
            if kw and kw not in parts:
                parts.append(kw)
    return parts


def build_default_queries(company: str, industry: str = "", city: str = "") -> list:
    """从公司信息推导默认查询集（模拟用户真实搜索行为）"""
    queries = [company, f"{company}怎么样"]
    if industry:
        queries.append(f"请推荐一家{industry}公司")
        if city:
            queries.append(f"推荐{city}的{industry}服务商")
    else:
        queries.append(f"{company}是做什么的")
    return queries[:4]


def _call_model(model_id: str, query: str) -> str:
    temp = MODEL_TEMPS.get(model_id, 0.3)
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": query}],
            "temperature": temp,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def assess_accuracy(answer: str, company_parts: list) -> str:
    """评估AI回答中品牌信息的准确度（高/中/低/无）"""
    has_name = any(part in answer for part in company_parts)
    has_business = any(kw in answer for kw in ["API", "网关", "大模型", "接入", "AI", "服务", "技术", "产品"])
    has_location = any(kw in answer for kw in ["成都", "四川", "北京", "上海", "深圳", "广州", "杭州"])
    has_detail = len(answer) > 200

    score = sum([has_name, has_business, has_location, has_detail])
    if score >= 3:
        return "高"
    elif score >= 2:
        return "中"
    elif score >= 1:
        return "低"
    return "无"


def detect_negative(answer: str, company_parts: list) -> bool:
    """检测回答中品牌提及是否伴随负面表述"""
    mentioned = any(part in answer for part in company_parts)
    if not mentioned:
        return False
    return any(neg in answer for neg in NEGATIVE_KEYWORDS)


class AIMonitor:
    name = "AIMonitor"
    description = "AI搜索监控：通过MzyToken多模型查询品牌展示率、引用情况"

    # 类级引用，保持向后兼容
    TEST_MODELS = TEST_MODELS
    MODEL_TEMPS = MODEL_TEMPS

    def execute(self, data):
        action = data.get("action", "monitor")
        if action == "monitor":
            return self._monitor(data)
        elif action == "test_query":
            return self._test_query(data)
        return {"success": False, "error": f"未知操作: {action}"}

    def _monitor(self, data):
        company = data.get("company", "")
        if not company:
            return {"success": False, "error": "缺少company参数"}

        keywords = data.get("keywords") or build_default_queries(
            company, data.get("industry", ""), data.get("city", "")
        )
        brand_keywords = data.get("brand_keywords") or []

        results = run_multi_model_monitor(company, keywords, brand_keywords)
        return {"success": True, "data": results}

    def _test_query(self, data):
        """对指定AI模型发起测试查询"""
        query = data.get("query", "")
        model = data.get("model", DEFAULT_MODEL)
        if not query:
            return {"success": False, "error": "缺少query参数"}

        try:
            answer = _call_model(model, query)
            return {"success": True, "data": {"query": query, "model": model, "answer": answer}}
        except requests.RequestException as e:
            return {"success": False, "error": f"请求失败: {e}"}


def run_multi_model_monitor(company: str, keywords: list, brand_keywords: list = None,
                            progress_cb=None) -> dict:
    """多模型并行查询品牌引用情况

    Args:
        progress_cb: 可选回调 fn(done_count, total, desc)，用于异步任务进度上报
    """
    company_parts = derive_company_parts(company, brand_keywords)
    models = list(TEST_MODELS.items())
    total_steps = len(models) * len(keywords[:4])
    done = [0]
    progress_lock = threading.Lock()

    def _report(desc):
        if progress_cb:
            with progress_lock:
                done[0] += 1
                progress_cb(done[0], total_steps, desc)

    def _query_model(model_id, model_info):
        platform_results = {
            "label": model_info["label"],
            "model": model_id,
            "queries": [],
            "mention_count": 0,
            "total_queries": 0,
            "display_rate": 0,
            "accuracy": "-",
            "note": "",
        }
        accuracy_scores = []
        error_count = 0

        for kw in keywords[:4]:
            try:
                answer = _call_model(model_id, kw)
                mentioned = any(part in answer for part in company_parts)
                accuracy = assess_accuracy(answer, company_parts)
                negative = detect_negative(answer, company_parts)

                platform_results["queries"].append({
                    "query": kw,
                    "mentioned": mentioned,
                    "accuracy": accuracy,
                    "negative": negative,
                    "answer_length": len(answer),
                    "snippet": answer[:300],
                })
                platform_results["total_queries"] += 1
                if mentioned:
                    platform_results["mention_count"] += 1
                accuracy_scores.append(ACCURACY_SCORE[accuracy])
            except requests.RequestException as e:
                error_count += 1
                platform_results["queries"].append({"query": kw, "error": str(e)[:100]})
            finally:
                _report(f"{model_info['label']}: {kw[:20]}")

        if platform_results["total_queries"] > 0:
            platform_results["display_rate"] = round(
                platform_results["mention_count"] / platform_results["total_queries"] * 100, 1
            )
        if accuracy_scores:
            avg = sum(accuracy_scores) / len(accuracy_scores)
            platform_results["accuracy"] = max(ACCURACY_SCORE, key=lambda k: abs(ACCURACY_SCORE[k] - avg))
        platform_results["note"] = f"{error_count}个查询失败" if error_count else "全部查询成功"
        return model_info["icon"], platform_results

    results = {
        "company": company,
        "keywords": keywords,
        "mode": "production",
        "platforms": {},
        "overall": {
            "total_queries": 0,
            "total_mentions": 0,
            "total_negative": 0,
            "avg_display_rate": 0,
            "avg_accuracy": 0,
            "negative_rate": 0,
        },
    }

    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        futures = [executor.submit(_query_model, mid, minfo) for mid, minfo in models]
        for future in as_completed(futures):
            try:
                platform_key, platform_results = future.result()
            except Exception as e:
                logger.error("模型查询整体失败: %s", e)
                continue
            results["platforms"][platform_key] = platform_results
            results["overall"]["total_queries"] += platform_results["total_queries"]
            results["overall"]["total_mentions"] += platform_results["mention_count"]
            results["overall"]["total_negative"] += sum(
                1 for q in platform_results["queries"] if q.get("negative")
            )

    overall = results["overall"]
    if overall["total_queries"] > 0:
        overall["avg_display_rate"] = round(overall["total_mentions"] / overall["total_queries"] * 100, 1)
        overall["negative_rate"] = round(overall["total_negative"] / overall["total_queries"] * 100, 1)

    all_accuracy = [
        ACCURACY_SCORE[q["accuracy"]]
        for p in results["platforms"].values()
        for q in p["queries"]
        if "accuracy" in q
    ]
    if all_accuracy:
        overall["avg_accuracy"] = round(sum(all_accuracy) / len(all_accuracy), 1)

    return results


# ========== 异步任务模式（对齐 geo_benchmark 的 start/status 模式） ==========

def start_monitor_async(company: str, keywords: list = None, brand_keywords: list = None,
                        industry: str = "", city: str = "") -> str:
    """启动异步监控任务，返回task_id"""
    task_id = str(uuid.uuid4())[:8]
    queries = keywords or build_default_queries(company, industry, city)
    total_steps = len(TEST_MODELS) * len(queries[:4])

    with _TASKS_LOCK:
        _MONITOR_TASKS[task_id] = {
            "status": "running",
            "progress": 0,
            "total_steps": total_steps,
            "current_step": 0,
            "current_desc": "",
            "result": None,
            "error": None,
        }

    def _progress(done_count, total, desc):
        with _TASKS_LOCK:
            task = _MONITOR_TASKS.get(task_id)
            if task:
                task["current_step"] = done_count
                task["current_desc"] = desc
                task["progress"] = int(done_count / max(total, 1) * 95)

    def _worker():
        try:
            result = run_multi_model_monitor(company, queries, brand_keywords, progress_cb=_progress)
            with _TASKS_LOCK:
                _MONITOR_TASKS[task_id]["result"] = result
                _MONITOR_TASKS[task_id]["status"] = "done"
                _MONITOR_TASKS[task_id]["progress"] = 100
        except Exception as e:
            logger.error("异步监控失败: %s", e, exc_info=True)
            with _TASKS_LOCK:
                _MONITOR_TASKS[task_id]["error"] = str(e)
                _MONITOR_TASKS[task_id]["status"] = "failed"

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return task_id


def get_monitor_status(task_id: str) -> dict:
    """查询异步监控任务状态"""
    with _TASKS_LOCK:
        task = _MONITOR_TASKS.get(task_id)
        if not task:
            return {"error": "任务不存在", "known": list(_MONITOR_TASKS.keys())}
        return {"task_id": task_id, **task}
