"""GEO Platform - 核心Agent模块"""
from agents.page_diagnoser import PageDiagnoser
from agents.ai_monitor import AIMonitor
from agents.site_optimizer import SiteOptimizer
from agents.content_generator import ContentGenerator
from agents.report_generator import ReportGenerator

AGENTS = {
    "page_diagnoser": PageDiagnoser,
    "ai_monitor": AIMonitor,
    "site_optimizer": SiteOptimizer,
    "content_generator": ContentGenerator,
    "report_generator": ReportGenerator,
}


def get_agent(name):
    cls = AGENTS.get(name)
    if not cls:
        return None
    return cls()
