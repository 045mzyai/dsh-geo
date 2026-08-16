"""GEO Platform - 数据库模型与初始化"""
import sqlite3
import json
import os
from config import DB_PATH


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        plan TEXT DEFAULT 'free',
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        domain TEXT NOT NULL,
        backup_domain TEXT,
        icp TEXT,
        industry TEXT,
        city TEXT,
        description TEXT,
        geo_score INTEGER DEFAULT 0,
        geo_grade TEXT DEFAULT 'D',
        owner_id INTEGER,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS geo_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        report_type TEXT DEFAULT 'full',
        score INTEGER DEFAULT 0,
        grade TEXT DEFAULT 'D',
        summary TEXT,
        core_issue TEXT,
        core_advantage TEXT,
        raw_data TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS website_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        severity TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        page_url TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        resolved_at TEXT
    );

    CREATE TABLE IF NOT EXISTS source_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        level TEXT NOT NULL,
        platform TEXT,
        url TEXT,
        title TEXT,
        content_type TEXT,
        accuracy TEXT DEFAULT 'unknown',
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS ai_model_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        model_name TEXT NOT NULL,
        query_type TEXT,
        query_text TEXT,
        mentioned INTEGER DEFAULT 0,
        accuracy TEXT,
        rank_position INTEGER,
        content_source TEXT,
        tested_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS geo_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        metric_name TEXT NOT NULL,
        metric_value REAL,
        metric_unit TEXT,
        source TEXT,
        measured_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS competitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        competitor_name TEXT NOT NULL,
        competitor_domain TEXT,
        geo_score INTEGER DEFAULT 0,
        source_count INTEGER DEFAULT 0,
        ai_accuracy REAL DEFAULT 0,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS optimization_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        task_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'medium',
        roi_score REAL,
        status TEXT DEFAULT 'pending',
        result TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS keyword_expansions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        seed_keyword TEXT NOT NULL,
        dimension TEXT NOT NULL,
        expanded_keyword TEXT NOT NULL,
        recommendation_score INTEGER DEFAULT 0,
        business_score INTEGER DEFAULT 0,
        reason TEXT,
        ai_sourced INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS monitor_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        snapshot_type TEXT NOT NULL,
        model_name TEXT,
        total_queries INTEGER DEFAULT 0,
        mention_count INTEGER DEFAULT 0,
        display_rate REAL DEFAULT 0,
        accuracy_score REAL DEFAULT 0,
        detail_json TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS scheduled_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        job_type TEXT NOT NULL,
        cron_expr TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        last_run_at TEXT,
        next_run_at TEXT,
        run_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS diagnosis_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        url TEXT NOT NULL,
        score INTEGER DEFAULT 0,
        issues TEXT,
        summary TEXT,
        raw_data TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS chat_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        channel TEXT DEFAULT 'geo_basic',
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        model TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS company_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        url TEXT NOT NULL,
        title TEXT,
        role TEXT,
        score INTEGER DEFAULT 0,
        content TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS geo_ab_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        name TEXT NOT NULL,
        questions_json TEXT NOT NULL,
        platforms_json TEXT NOT NULL,
        results_json TEXT,
        status TEXT DEFAULT 'created',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        completed_at TEXT
    );
    """)
    conn.commit()

    # Migration: add owner_id to existing companies table
    try:
        conn.execute("ALTER TABLE companies ADD COLUMN owner_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


def get_company(company_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def seed_mzy_data():
    """导入木子杨GEO分析报告数据"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM companies WHERE domain='mzyai.com'")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    cur.execute("""
    INSERT INTO companies (name, domain, backup_domain, icp, industry, city, description, geo_score, geo_grade)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("四川木子杨科技有限公司", "mzyai.com", "mzyal.com",
          "蜀ICP备2024073001号-1", "AI网关聚合服务", "成都",
          "提供35+大模型统一API接入服务(MzyToken)，2025年入选国家级科技型中小企业",
          32, "D"))

    company_id = cur.lastrowid

    cur.execute("""
    INSERT INTO geo_reports (company_id, report_type, score, grade, summary, core_issue, core_advantage)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (company_id, "full", 32, "D",
          "综合得分32/130分，评级D级（基础薄弱级），处于成都本地中小科技服务行业后20%分位",
          "官方信源体系极不完整，官网功能单一且缺失核心信任要素，全网高质量信源不足10条，无主动UGC口碑沉淀，大模型可采信业务信息极度匮乏，品牌数字信任基础几乎空白",
          "拥有已备案的独立官网且核心业务（AI网关聚合）呈现清晰，具备基础线上服务载体；2025年入选国家级科技型中小企业，具备官方资质背书；曾获得行业媒体公开报道，具备少量第三方公信力素材"))

    # 官网技术问题
    issues = [
        ("fatal", "域名失效", "备用域名mzyal.com完全失效", "mzyal.com"),
        ("high", "结构化数据缺失", "全站无JSON-LD结构化数据标记，大模型无法快速提取企业主体、业务、联系方式等核心信息", "全站"),
        ("high", "llms.txt缺失", "根目录缺失llms.txt与ai.txt文件，大模型无法定向抓取官网权威内容", "根目录"),
        ("medium", "信任页面缺失", "无独立的关于我们、联系我们页面，未公开企业完整介绍、团队信息、实体地址、联系电话", "全站"),
        ("medium", "移动端适配问题", "窄屏设备下部分模块文字溢出、按钮错位", "首页"),
        ("low", "时间戳缺失", "所有页面无明确更新时间戳，大模型无法判断内容时效性", "全站"),
    ]
    for sev, cat, desc, url in issues:
        cur.execute("INSERT INTO website_issues (company_id, severity, category, title, description, page_url) VALUES (?,?,?,?,?,?)",
                    (company_id, sev, cat, cat, desc, url))

    # 核心指标
    metrics = [
        ("官网内容被大模型引用率", 8, "%", "800个大模型回答样本"),
        ("官网核心页面收录率", 42, "%", "5个核心页面"),
        ("JSON-LD覆盖率", 0, "%", "7个页面样本"),
        ("核心文档HTML化转化率", 30, "%", "10份核心文档"),
        ("llms.txt完整性评分", 0, "分", "根目录文件检测"),
        ("官网内容整体完整度", 62, "%", "7个页面样本"),
        ("转化便捷性评分", 35, "分", "100分制"),
        ("S级信源数量", 3, "条", "全网信源质检"),
        ("A1/A2级信源数量", 1, "条", "全网信源质检"),
        ("B级信源数量", 5, "条", "全网信源质检"),
        ("信源总量", 13, "条", "全网信源质检"),
        ("S级信源引用率", 11.4, "%", "大模型引用分析"),
        ("信息准确率", 59.6, "%", "大模型实测"),
        ("品牌词平均排名", 11.5, "位", "大模型实测"),
        ("负面提及率", 1.5, "%", "全平台检索"),
    ]
    for name, val, unit, src in metrics:
        cur.execute("INSERT INTO geo_metrics (company_id, metric_name, metric_value, metric_unit, source) VALUES (?,?,?,?,?)",
                    (company_id, name, val, unit, src))

    # 竞品
    competitors = [
        ("成都木风未来科技有限公司", None, 0, 58, 82.3),
        ("成都小火科技有限公司", None, 0, 93, 88.5),
        ("成都云智未来科技有限公司", None, 0, 49, 76.4),
    ]
    for name, domain, score, sources, accuracy in competitors:
        cur.execute("INSERT INTO competitors (company_id, competitor_name, competitor_domain, geo_score, source_count, ai_accuracy) VALUES (?,?,?,?,?,?)",
                    (company_id, name, domain, score, sources, accuracy))

    # 优化任务（按ROI排序）
    tasks = [
        ("content", "垂直赛道专业占位", "打造成都本土AI网关聚合服务商精准定位，全平台统一业务表述，快速建立垂直赛道认知", "high", 8.2),
        ("fix", "错误信息批量修正", "一次性修正全网错误百科与工商信息，快速提升大模型信息准确率", "high", 7.9),
        ("content", "小微企业客群定向内容", "针对小微企业输出低成本AI接入系列内容，精准匹配目标客群需求", "medium", 6.5),
        ("product", "轻量化产品包装", "突出产品5分钟接入、低价折扣等优势，与竞品的重服务模式形成差异", "medium", 5.8),
        ("tech", "部署llms.txt", "在网站根目录部署llms.txt和ai.txt，指引大模型抓取官网权威内容", "high", 7.5),
        ("tech", "部署JSON-LD结构化数据", "全站添加Organization/Product/Service等Schema标记", "high", 7.2),
        ("tech", "修复备用域名", "修复mzyal.com或做301重定向到mzyai.com", "high", 6.0),
        ("content", "添加关于我们/联系我们页面", "公开企业完整介绍、团队信息、实体地址、联系电话", "medium", 5.5),
        ("tech", "移动端适配修复", "修复窄屏设备下文字溢出、按钮错位问题", "medium", 4.0),
        ("content", "处理经营异常名录", "完成年度报告公示，申请移出经营异常名录", "high", 8.0),
    ]
    for ttype, title, desc, pri, roi in tasks:
        cur.execute("INSERT INTO optimization_tasks (company_id, task_type, title, description, priority, roi_score) VALUES (?,?,?,?,?,?)",
                    (company_id, ttype, title, desc, pri, roi))

    conn.commit()
    conn.close()
    print(f"[INFO] 木子杨GEO数据已导入 (company_id={company_id})")


if __name__ == "__main__":
    init_db()
    seed_mzy_data()
    print("[INFO] 数据库初始化完成")
