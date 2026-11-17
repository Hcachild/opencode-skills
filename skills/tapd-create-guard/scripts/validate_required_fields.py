#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAPD 创建工作项必填字段校验器
依据《TAPD操作指导和规范要求》V1.0（2026-10-13 核对最新版）

用法:
  单条:  python validate_required_fields.py --type story --data '{"name":"x","priority":"P1",...}'
  批量:  python validate_required_fields.py --items-file items.json
  管道:  cat items.json | python validate_required_fields.py --items-file -
  清单:  python validate_required_fields.py --list

可选字段 parent_type（父需求类型）：传 epic/feature/story/task、中文名（史诗故事/特性/需求/任务）
或 workitem_type_id 均可。传了就能自动拦住「Story 挂 Story」「Task 挂 Task」等同级/越级挂载；
不传则只能提示调用方自行核实父级类型（脚本离线查不到 TAPD）。

枚举取值：只能填该空间**已配置**的选项（优先级/项目分类/分类/需求类型/任务类型 等）。
TAPD 已设置好的字段名与枚举值不得新增 / 改名 / 删除 —— 不在已知选项内时默认给提示，
加 `--strict-enum` 升级为阻断错误。

退出码: 0=全部通过  1=存在缺失(不得继续创建)  2=输入格式错误
"""
import argparse
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------- 类型与字段

TYPE_ALIASES = {
    "epic": "epic", "史诗": "epic", "史诗故事": "epic", "0033": "epic",
    "1132496738001000033": "epic",
    "feature": "feature", "特性": "feature", "版本": "feature", "0032": "feature",
    "1132496738001000032": "feature",
    "story": "story", "需求": "story", "故事": "story", "0031": "story",
    "1132496738001000031": "story",
    "task": "task", "任务": "task", "0035": "task",
    "1132496738001000035": "task",
    "bug": "bug", "缺陷": "bug", "生产缺陷": "bug", "提bug": "bug", "提缺陷": "bug",
}

TYPE_LABELS = {
    "epic": "Epic（史诗故事）",
    "feature": "Feature（特性）",
    "story": "Story（需求）",
    "task": "Task（任务）",
    "bug": "Bug（缺陷）",
}

FIELD_ALIASES = {
    "标题": "name", "name": "name", "title": "name",
    "详细描述": "description", "description": "description", "描述": "description",
    "父需求": "parent_id", "parent_id": "parent_id", "父需求id": "parent_id",
    "父需求类型": "parent_type", "parent_type": "parent_type",
    "parent_workitem_type_id": "parent_type", "父需求工作项类型": "parent_type",
    "优先级": "priority", "priority": "priority",
    "处理人": "owner", "owner": "owner",
    "项目分类": "custom_field_12", "custom_field_12": "custom_field_12",
    "项目Owner": "custom_field_13", "项目owner": "custom_field_13",
    "custom_field_13": "custom_field_13",
    "Epic归属项目或系统": "custom_field_36", "custom_field_36": "custom_field_36",
    "分类": "category_id", "category_id": "category_id",
    "需求提出方": "custom_field_two", "custom_field_two": "custom_field_two",
    "需求类型": "custom_field_five", "custom_field_five": "custom_field_five",
    "计划需求评审时间": "custom_field_24", "custom_field_24": "custom_field_24",
    "任务类型": "custom_field_19", "custom_field_19": "custom_field_19",
    "预计开始": "begin", "begin": "begin",
    "预计结束": "due", "due": "due",
    "预估工时": "effort", "effort": "effort",
    # ---- 缺陷（Bug）字段：36495762（生产缺陷处理）与 32496738（需求池）两个空间都有
    "严重程度": "severity", "severity": "severity",
    "开发人员": "de", "de": "de",
    "测试人员": "te", "te": "te",
    "所属系统": "所属系统", "缺陷提出方": "缺陷提出方", "问题来源": "问题来源",
    "关联需求": "parent_id",
    "缺陷类型": "缺陷类型",
    "迭代": "iteration_id", "iteration_id": "iteration_id",
    "引入阶段": "引入阶段",
    "解决方法": "resolution", "resolution": "resolution",
    # 「拒绝原因」字段 ID 因空间而异：32496738=custom_field_two，36495762=custom_field_four（2026-10-13 起必填）
    # 别名仅作参考；流转前以目标空间工作流实查为准（配置可能被管理员调整）
    "拒绝原因": "custom_field_two",
    "custom_field_four": "custom_field_four",
    "评论": "remarks", "remarks": "remarks",
}

# (字段ID, 界面名, 校验种类, 取值提示)
REQUIRED = {
    "epic": [
        ("name", "标题", "text", "工作项名称，非空"),
        ("custom_field_12", "项目分类", "enum", "可选：项目 / 系统 / 其他"),
        ("priority", "优先级", "enum", "可选：P0 / P1 / P2 / P3"),
        ("owner", "处理人", "user", "填人员姓名"),
        ("custom_field_13", "项目Owner", "user", "填人员姓名"),
        ("custom_field_36", "Epic归属项目或系统", "text",
         "25 项枚举之一（见 SKILL.md，如 百运科技-SN318重构项目 / 财务专项 / WMS系统）"),
    ],
    "feature": [
        ("name", "标题", "text", "工作项名称，非空"),
        ("parent_id", "父需求", "ref", "必须关联 Epic（史诗故事）—— 不得挂 Feature / Story / Task"),
        ("priority", "优先级", "enum", "可选：P0 / P1 / P2 / P3"),
        ("owner", "处理人", "user", "填人员姓名"),
    ],
    "story": [
        ("name", "标题", "text", "工作项名称，非空"),
        ("description", "详细描述", "richtext",
         "不能为空，且要写成 HTML 结构：<p> 分段 + <strong> 小标题加粗 + <ul><li> 分条"
         "（纯文本 \n 换行会被并进同一个 <p>，界面全挤成一行）；空标签(<p></p>)视为未填"),
        ("parent_id", "父需求", "ref", "必须关联 Feature（特性）—— ✗ 不得挂 Story（同级），✗ 不得越级挂 Epic"),
        ("category_id", "分类", "enum",
         "可选：产品需求 / 技术需求 / 数据需求 / 日常运维类 / 非项目类工作；"
         "API 创建须传选项 ID（技术需求=1132496738001000029），传中文会静默写不进去"),
        ("custom_field_two", "需求提出方", "text", "填需求提出人姓名或部门"),
        ("custom_field_five", "需求类型", "enum",
         "可选：新功能/功能优化/需求缺陷/技术重构/日常运维/接口对接/数据报表/"
         "算法模型/AI能力集成/合规安全/运营活动/UI交互/其他优化"),
        ("priority", "优先级", "enum", "可选：P0 / P1 / P2 / P3"),
        ("owner", "处理人", "user", "填人员姓名"),
        ("custom_field_24", "计划需求评审时间", "date", "日期格式 YYYY-MM-DD"),
    ],
    "task": [
        ("name", "标题", "text", "工作项名称，非空"),
        ("description", "详细描述", "richtext",
         "不能为空，且要写成 HTML 结构：<p> 分段 + <strong> 小标题加粗 + <ul><li> 分条"
         "（纯文本 \n 换行会被并进同一个 <p>，界面全挤成一行）；空标签(<p></p>)视为未填"),
        ("parent_id", "父需求", "ref", "必须关联 Story（需求）—— ✗ 不得挂 Task（同级），✗ 不得越级挂 Feature / Epic"),
        ("custom_field_19", "任务类型", "enum",
         "可选：需求&调研 / UI设计 / 技术设计 / 开发 / 测试 / 验收 / 管理 / 其他"),
        ("priority", "优先级", "enum", "可选：P0 / P1 / P2 / P3"),
        ("owner", "处理人", "user", "填人员姓名"),
        ("begin", "预计开始", "date", "日期格式 YYYY-MM-DD"),
        ("due", "预计结束", "date", "日期格式 YYYY-MM-DD"),
        ("effort", "预估工时", "number", "单位 h（小时），>24h 会提示与主管确认工时合理性（≤24h 不提示，不阻断）"),
    ],
    # 缺陷：两个空间都有（36495762 生产缺陷处理 / 32496738 需求池），创建/修改/流转全程需用户确认
    # 本清单基于 36495762 团队规范；32496738 规范未单列，创建前必须把该空间完整必填清单给用户确认
    "bug": [
        ("name", "标题", "text", "工作项名称，非空"),
        ("severity", "严重程度", "enum", "英文枚举：fatal 致命 / serious 严重 / normal 一般 / prompt 提示 / advice 建议（传中文或 P1 无效）"),
        ("de", "开发人员", "user", "填人员姓名"),
        ("owner", "处理人", "user", "填人员姓名（create_bug 接口对应字段 current_owner）"),
        ("所属系统", "所属系统", "enum", "36495762 已配置选项（百运官网 / FreightShop / 询价后台 / … / 其他，25 项）"),
        ("缺陷提出方", "缺陷提出方", "text", "缺陷提出人姓名或部门"),
        ("问题来源", "问题来源", "enum", "36495762 已配置选项：业务反馈 / 内部自查 / 监控告警 / 数据对账 / 其他"),
    ],
}

# ---- 需求池空间（32496738）缺陷创建必填：手册第 4 章「创建缺陷涉及字段」（原文"必填字段（7个）"）
# 与生产缺陷空间（36495762）清单不同；item 带 workspace_id 时按空间选择清单
REQUIRED_BUG_POOL = {
    "bug": [
        ("name", "标题", "text", "工作项名称，非空"),
        ("description", "详细描述", "richtext",
         "内容必填（手册：填写标题&内容）—— 写复现步骤、期望结果、实际结果；"
         "HTML 结构：<p> 分段 + <strong> 小标题加粗 + <ul><li> 分条"),
        ("parent_id", "关联需求", "ref", "必填 —— 缺陷必须关联对应需求（不得为空或 0）"),
        ("severity", "严重程度", "text", "按该空间已配置的严重程度选项填"),
        ("owner", "处理人", "user", "填人员姓名（接口字段 current_owner）"),
        ("de", "开发人员", "user", "填人员姓名"),
        ("缺陷类型", "缺陷类型", "text", "按该空间已配置的缺陷类型选项填"),
        ("iteration_id", "迭代", "text", "关联所属迭代"),
        ("引入阶段", "引入阶段", "text", "按该空间已配置选项填（该缺陷是哪个阶段引入的）"),
    ],
}

CATEGORY_ID_MAP = {
    "产品需求": "1132496738001000027",
    "技术需求": "1132496738001000029",
    "数据需求": "1132496738001000033",
    "日常运维类": "1132496738001000034",
    "非项目类工作": "1132496738001000040",
}

ENUM_OPTIONS = {
    "priority": ["P0", "P1", "P2", "P3"],
    "custom_field_12": ["项目", "系统", "其他"],
    "category_id": ["产品需求", "技术需求", "数据需求", "日常运维类", "非项目类工作"],
    "custom_field_five": ["新功能", "功能优化", "需求缺陷", "技术重构", "日常运维",
                          "接口对接", "数据报表", "算法模型", "AI能力集成", "合规安全",
                          "运营活动", "UI交互", "其他优化"],
    "custom_field_19": ["需求&调研", "UI设计", "技术设计", "开发", "测试", "验收", "管理", "其他"],
    # 缺陷严重程度：接口级固定枚举，只收英文值（2026-10-13 实测；中文/P1 传了无效）
    "severity": ["fatal", "serious", "normal", "prompt", "advice"],
    # 36495762 生产缺陷空间实测选项（2026-10-13 拉取；可能被管理员调整，校验提示以实时拉取为准）
    "所属系统": ["百运官网", "FreightShop", "询价后台", "百运网后台管理系统", "百运科技运小星",
                 "智慧工单", "知识库&知识库后台", "中技客户中心业务系统（BS）", "中技后勤打单系统",
                 "中技后勤操作CS系统", "百运供应商系统", "百运移动端", "百运OA", "取送易",
                 "中技官网", "中技OA", "快递第三方对接", "中技运小星", "互联通", "易境通",
                 "中技理货APP", "中技RPA系统", "中技BSA系统", "财务系统", "其他"],
    "问题来源": ["业务反馈", "内部自查", "监控告警", "数据对账", "其他"],
}

# 缺陷严重程度中文 → 英文枚举映射（用户给中文时提示正确英文值）
SEVERITY_CN_MAP = {"致命": "fatal", "严重": "serious", "一般": "normal",
                   "提示": "prompt", "建议": "advice"}

# ---- 父需求层级铁律：父需求只能是「上一级」，严禁同级挂载 / 越级挂载
#      Feature←Epic / Story←Feature / Task←Story；Epic 是顶层，不得有父需求
PARENT_TYPE_RULE = {"feature": "epic", "story": "feature", "task": "story"}
PARENT_TYPE_LABEL_CN = {"epic": "史诗故事（Epic）", "feature": "特性（Feature）",
                        "story": "需求（Story）", "task": "任务（Task）"}
# 允许用这些写法描述父需求类型（含 TAPD 界面中文名、英文名、workitem_type_id）
PARENT_TYPE_ALIASES = {
    "epic": "epic", "史诗故事": "epic", "史诗": "epic", "项目": "epic",
    "1132496738001000033": "epic",
    "feature": "feature", "特性": "feature", "版本": "feature",
    "1132496738001000032": "feature",
    "story": "story", "需求": "story", "故事": "story",
    "1132496738001000031": "story",
    "task": "task", "任务": "task",
    "1132496738001000035": "task",
}


def norm_parent_type(raw):
    """把父需求类型的各种写法归一化为 epic/feature/story/task；识别不了返回 None。"""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    return PARENT_TYPE_ALIASES.get(s) or PARENT_TYPE_ALIASES.get(str(raw).strip())


EMPTY_TOKENS = {"", "0", "0.0", "-1", "none", "null", "nan", "-", "—", "未分类", "无"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
TAG_RE = re.compile(r"<[^>]+>")

# ---- 标题 / 描述模板（规范要求，默认以「提示」呈现，--strict-template 时升级为阻断错误）
STORY_TITLE_RE = re.compile(r"^【.+?】\s*\S+")
TASK_TITLE_RE = re.compile(
    r"^(需求&调研|需求调研|UI设计|设计|技术设计|开发|测试|验收|管理|其他)\s*[-—－]\s*\S+")
STORY_DESC_SECTIONS = ["需求背景", "需求描述", "验收标准"]
TASK_DESC_SECTIONS = ["任务说明", "完成定义", "依赖"]
# ---- 缺陷模板（2026-10-13 用户提供，两空间标题模板不同）
BUG_TITLE_PROD_RE = re.compile(r"^【[^】]+】【[^】]+】\S+")   # 36495762：【系统名称】【模块或功能名称】描述
BUG_TITLE_POOL_RE = re.compile(r"^【[^】]+】\S+")             # 32496738：【系统名称 版本号】描述
BUG_DESC_SECTIONS = ["环境", "版本", "复现步骤", "预期结果", "实际结果", "附件"]


# ---- 时间顺序约束（2026-10-13 用户要求：不满足→醒目提醒，用户坚持→放行，不阻断）
# Story 计划时间链（字段 ID 为需求池 32496738 实测）；Task 用 begin/due
TIME_ORDER_RULES = {
    "story": [
        ("custom_field_24", "计划需求评审时间"),
        ("custom_field_22", "计划开发开始时间"),
        ("custom_field_20", "计划提测时间"),
        ("custom_field_28", "计划测试开始时间"),
        ("custom_field_21", "计划测试完成时间"),
        ("custom_field_six", "计划上线时间"),
    ],
    "task": [
        ("begin", "预计开始"),
        ("due", "预计结束"),
    ],
}
TIME_CHAIN_TEXT = {
    "story": "计划时间链应满足：评审 ≤ 开发开始 ≤ 提测 ≤ 测试开始 ≤ 测试完成 ≤ 上线",
    "task": "预计结束不应早于预计开始",
}


def check_time_order(t, item):
    """时间顺序约束：后一环节早于前一环节时给醒目提醒（warning，不阻断——用户坚持原值可放行）。"""
    rules = TIME_ORDER_RULES.get(t)
    if not rules:
        return []
    warns = []
    parsed = []
    for fid, label in rules:
        raw = item.get(fid)
        s = str(raw).strip() if raw is not None else ""
        parsed.append((fid, label, s if DATE_RE.match(s) else None))
    for (f1, l1, v1), (f2, l2, v2) in zip(parsed, parsed[1:]):
        if v1 and v2 and v2 < v1:
            warns.append(
                "⏰ 时间顺序提醒：%s（%s）早于 %s（%s）—— %s；请确认是否符合计划。"
                "若确认坚持原值可放行（本提醒不阻断创建，但须向用户醒目展示）"
                % (l2, v2, l1, v1, TIME_CHAIN_TEXT[t]))
    return warns


def strip_html(s):
    """去 HTML 标签并还原常见空白实体，用于判断富文本是否为空。"""
    t = TAG_RE.sub(" ", str(s if s is not None else ""))
    for ent in ("&nbsp;", "&emsp;", "&ensp;", "&#160;", "\u200b"):
        t = t.replace(ent, " ")
    return t.strip()


# ---------------------------------------------------------------- 校验逻辑

def norm_type(raw):
    if raw is None:
        return None
    return TYPE_ALIASES.get(str(raw).strip().lower()) or TYPE_ALIASES.get(str(raw).strip())


def norm_item(raw):
    """把中文界面名统一成字段 ID。"""
    out = {}
    for k, v in (raw or {}).items():
        key = str(k).strip()
        out[FIELD_ALIASES.get(key, key)] = v
    return out


def is_blank(v):
    if v is None:
        return True
    if isinstance(v, (list, tuple, dict)):
        return len(v) == 0
    s = str(v).strip()
    return s.lower() in EMPTY_TOKENS


def check_value(field, kind, value, strict_enum=False):
    """返回 (error_msg or None, warning_msg or None)"""
    if is_blank(value):
        return "缺失", None

    if kind == "richtext":
        if not strip_html(value):
            return "缺失", None
        return None, None

    if kind == "number":
        try:
            num = float(str(value).strip().replace("h", "").replace("H", ""))
        except Exception:
            return "不是有效数字", None
        warn = None
        if num <= 0:
            return "必须大于 0（单位：小时）", None
        # 预估工时 >24h：提示与主管确认（不阻断，允许存在超过 24h 的任务——用户 2026-10-13 要求；=24h 不提示）
        if num > 24:
            warn = "⏰ 预估工时 %g h 已达到/超过 24h —— 请与主管确认工时的合理性（提示不阻断，允许存在超过 24h 的任务）" % num
        return None, warn

    if kind == "date":
        if not DATE_RE.match(str(value).strip()):
            return "日期格式应为 YYYY-MM-DD", None
        return None, None

    if kind == "enum" and field in ENUM_OPTIONS:
        s = str(value).strip()
        ok_values = set(ENUM_OPTIONS[field])
        if field == "category_id":
            ok_values |= set(CATEGORY_ID_MAP.values())
        if s not in ok_values:
            # 严重程度特殊处理：用户给中文时，提示正确的英文枚举值
            if field == "severity" and s in SEVERITY_CN_MAP:
                return ("严重程度须传英文枚举「%s」（中文「%s」接口不收，传了会静默失败）"
                        % (SEVERITY_CN_MAP[s], s)), None
            msg = ("取值「%s」不是该空间已配置的枚举选项（可选：%s）—— "
                   "TAPD 已设置好的字段名与枚举值不得新增 / 改名 / 删除，"
                   "只能是上述已有选项之一；若确需新选项，请让管理员在 TAPD 界面配置，不要用别的值顶替"
                   % (s, " / ".join(ENUM_OPTIONS[field])))
            if strict_enum:
                return msg, None
            return None, msg

    if kind == "ref":
        s = str(value).strip()
        if s in ("0", "-1"):
            return "未关联（值为 %s）" % s, None

    return None, None


def check_template(t, title, description, ws=None):
    """标题 / 描述模板合规检查，返回提示列表。"""
    tips = []
    plain_desc = strip_html(description)

    if t == "story":
        if title and not STORY_TITLE_RE.match(title):
            tips.append("标题未按模板「【模块名称】简要描述」书写，如：『【价格表管理】支持批量询价导入』")
        if plain_desc:
            miss = [s for s in STORY_DESC_SECTIONS if s not in plain_desc]
            if miss:
                tips.append("详细描述缺少模板段落：%s（标准模板见 SKILL.md）"
                            % "、".join("【%s】" % s for s in miss))
    elif t == "task":
        if title and not TASK_TITLE_RE.match(title):
            tips.append("标题未按模板「任务类型-动作」书写，如：『开发-询价接口客户信息非必填改造』")
        if plain_desc:
            miss = [s for s in TASK_DESC_SECTIONS if s not in plain_desc]
            if miss:
                tips.append("详细描述缺少模板段落：%s（标准模板见 SKILL.md）" % "、".join(miss))
    elif t == "bug":
        # 两空间标题模板不同：36495762 双【】（系统名+模块名）；32496738 单【】内含"系统名称 版本号"
        if title:
            if ws and "32496738" in ws:
                if not BUG_TITLE_POOL_RE.match(title):
                    tips.append("标题未按需求池缺陷模板「【系统名称 版本号】简洁描述缺陷」书写，"
                                "如：『【百运CRM V1.3】列表导出报错』")
            elif ws and "36495762" in ws:
                if not BUG_TITLE_PROD_RE.match(title):
                    tips.append("标题未按生产缺陷模板「【系统名称】【模块或功能名称】简洁描述缺陷主题」书写，"
                                "如：『【百运CRM】【价格表】批量导出勾选失效』")
            elif not (BUG_TITLE_PROD_RE.match(title) or BUG_TITLE_POOL_RE.match(title)):
                tips.append("标题未按缺陷模板书写（两空间模板不同，见 SKILL.md）：生产缺陷="
                            "「【系统名称】【模块或功能名称】描述」；需求池=「【系统名称 版本号】描述」")
        if plain_desc:
            miss = [s for s in BUG_DESC_SECTIONS if s not in plain_desc]
            if miss:
                tips.append("详细描述缺少模板段落：%s（缺陷描述模板见 SKILL.md —— "
                            "【环境】【版本】【复现步骤】【预期结果】【实际结果】【附件】，需分条换行）"
                            % "、".join("【%s】" % s for s in miss))

    # ---- 描述结构化检查（2026-10-13 新增）
    # TAPD 描述是富文本：纯文本的 "\n" 换行会被并进同一个 <p>，界面上全挤成一行。
    # 必须用 <p> 分段、<strong> 加粗小标题、<ul><li> 分条。
    if t in ("story", "task", "epic", "feature", "bug") and description and plain_desc:
        raw = str(description)
        lacks = []
        if "<p" not in raw:
            lacks.append("<p>（分段）")
        if "<strong" not in raw and "<b>" not in raw:
            lacks.append("<strong>（小标题加粗）")
        if "<ul" not in raw and "<ol" not in raw:
            lacks.append("<ul><li>（分条列表）")
        if lacks:
            tips.append("详细描述缺少结构化标签：%s —— 纯文本换行（\\n）在 TAPD 里会被并进同一个段落、"
                        "界面上全挤成一行；请改用 HTML 结构（模板见 SKILL.md「描述结构化写法」）"
                        % "、".join(lacks))
    return tips


def validate_one(raw_item, strict_template=False, strict_enum=False):
    item = norm_item(raw_item)
    t = norm_type(item.get("type") or item.get("workitem_type") or item.get("类型"))
    title = item.get("name") or item.get("title") or item.get("标题") or "(未命名)"

    if not t:
        return {"ok": False, "index": None, "type": None, "type_label": None,
                "title": title, "missing": [],
                "errors": ["无法识别工作项类型（type）—— 请填 epic / feature / story / task / bug（缺陷）"],
                "warnings": []}

    missing, warnings, errors = [], [], []
    # 缺陷按目标空间选择必填清单（两空间不同，依据手册第 4 / 7 章）
    required_map = REQUIRED
    ws = str(item.get("workspace_id") or "").strip()
    if t == "bug":
        if "32496738" in ws:
            required_map = REQUIRED_BUG_POOL
        elif "36495762" in ws:
            required_map = REQUIRED
        else:
            warnings.append(
                "未提供 workspace_id —— **请先向用户确认目标空间**（36495762 生产缺陷处理 / "
                "32496738 需求池，两空间必填清单不同），确认后在 item 里加 \"workspace_id\" 重新校验；"
                "当前仅暂按 36495762 清单预校验，不作为创建依据（不得默认空间、不得猜测）")
    for fid, label, kind, hint in required_map.get(t, []):
        err, warn = check_value(fid, kind, item.get(fid), strict_enum=strict_enum)
        if err:
            if err == "缺失":
                missing.append({"field": fid, "label": label, "hint": hint})
            else:
                errors.append("%s（%s）：%s" % (label, fid, err))
        if warn:
            warnings.append(warn)

    nm = str(item.get("name") or item.get("title") or "").strip()
    if nm and len(nm) < 4:
        warnings.append("标题「%s」偏短，建议写清具体做什么" % nm)

    if t == "bug":
        if "32496738" in ws:
            ws_tip = "已按需求池 32496738 缺陷清单校验（手册第 4 章：标题&内容 + 7 项）"
        elif "36495762" in ws:
            ws_tip = "已按生产缺陷处理 36495762 缺陷清单校验（手册第 7 章：标题 + 6 项）"
        else:
            ws_tip = "未提供 workspace_id，默认按 36495762 清单校验（见上条提示）"
        warnings.append("缺陷两空间必填不同 —— " + ws_tip +
                        "；缺陷的创建 / 修改 / 状态流转全程都需用户确认后才能写 TAPD")

    # ---- 时间顺序约束：不满足 → 醒目提醒（不阻断，用户坚持原值可放行）
    warnings.extend(check_time_order(t, item))

    cat = str(item.get("category_id") or "").strip()
    if t == "story" and cat in CATEGORY_ID_MAP:
        warnings.append("分类填的是中文「%s」—— 经 API 创建时必须传 ID（%s），传中文会被静默写成 0"
                        % (cat, CATEGORY_ID_MAP[cat]))

    if t in ("feature", "story", "task") and is_blank(item.get("custom_field_36")):
        warnings.append("未提供「Epic归属项目或系统」(custom_field_36) —— 该字段应由父级继承"
                        "（Feature←Epic / Story←Feature / Task←Story）；请先查父级取值填入创建参数，或创建后回填")

    # ---- 父需求层级铁律：只能挂「上一级」，禁止同级挂载（Story→Story / Task→Task）与越级挂载
    pid = item.get("parent_id")
    pt = norm_parent_type(item.get("parent_type"))
    if t == "epic":
        if not is_blank(pid):
            errors.append("Epic（史诗故事）是顶层工作项，不能挂父需求 —— parent_id 必须为空")
    elif t in PARENT_TYPE_RULE:
        expect = PARENT_TYPE_RULE[t]
        if pt is None:
            if not is_blank(pid):
                warnings.append(
                    "未能判断父需求「%s」的类型 —— 脚本离线查不了。请用 mcp__tapd__get_stories_or_tasks "
                    "按该 id 查 workitem_type_id 确认：%s 的父需求必须是 %s；"
                    "若查出父需求与自身同级（如 Story 挂 Story、Task 挂 Task）必须改掉。"
                    "（也可直接传 parent_type 让本脚本自动判定）"
                    % (pid, TYPE_LABELS[t], PARENT_TYPE_LABEL_CN[expect]))
        elif pt == t:
            errors.append("父需求类型与自身相同 —— %s 的父需求不能是 %s，禁止同级挂载，必须挂到 %s"
                          % (TYPE_LABELS[t], PARENT_TYPE_LABEL_CN[t], PARENT_TYPE_LABEL_CN[expect]))
        elif pt != expect:
            errors.append("父需求类型是 %s，但 %s 的父需求必须是 %s（禁止越级 / 挂错层级）"
                          % (PARENT_TYPE_LABEL_CN[pt], TYPE_LABELS[t], PARENT_TYPE_LABEL_CN[expect]))

    tmpl_tips = check_template(t, nm, item.get("description"), ws)
    if strict_template:
        errors.extend(tmpl_tips)
    else:
        warnings.extend(tmpl_tips)

    return {
        "ok": not missing and not errors,
        "type": t,
        "type_label": TYPE_LABELS[t],
        "title": title,
        "missing": missing,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------- 输出

def render_text(report):
    lines = []
    lines.append("TAPD 创建工作项必填字段校验")
    lines.append("=" * 46)
    lines.append("共 %d 条：通过 %d，未通过 %d" % (report["total"], report["passed"], report["failed"]))
    lines.append("")
    for i, r in enumerate(report["results"], 1):
        flag = "✅ 通过" if r["ok"] else "❌ 未通过"
        lines.append("【%d】%s  %s - 「%s」" % (i, flag, r.get("type_label") or "类型未知", r["title"]))
        for m in r["missing"]:
            lines.append("   · 缺 %s（%s）—— %s" % (m["label"], m["field"], m["hint"]))
        for e in r["errors"]:
            lines.append("   · 错误 %s" % e)
        for w in r["warnings"]:
            lines.append("   · 提示 %s" % w)
        lines.append("")
    if report["ok"]:
        if report.get("warnings", 0):
            lines.append("结论：必填字段全部通过，但另有 %d 条提示 —— 其中「枚举取值未命中已配置选项」「模板不符」"
                         "两类必须先与用户确认 / 改正后才能创建（见 SKILL.md 第 5 步）。"
                         % report["warnings"])
        else:
            lines.append("结论：全部通过，可以创建（仍需用户确认整版草稿）。")
    else:
        lines.append("结论：存在缺失或错误，**不得创建**，请补齐/改正后重跑校验。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--items-file", help="待创建工作项 JSON 文件（数组或单对象）；传 - 从 stdin 读")
    ap.add_argument("--type", help="单条模式：工作项类型 epic/feature/story/task")
    ap.add_argument("--data", help="单条模式：该工作项的 JSON")
    ap.add_argument("--format", choices=["text", "json"], default="text", help="输出格式，默认 text")
    ap.add_argument("--strict-template", action="store_true",
                    help="把标题/描述不符合模板当作错误（默认仅提示、不阻断）")
    ap.add_argument("--strict-enum", action="store_true",
                    help="把枚举取值不在该空间已配置选项内当作错误（默认仅提示）")
    ap.add_argument("--list", action="store_true", help="打印各类型必填字段清单后退出")
    args = ap.parse_args()

    if args.list:
        for t in ("epic", "feature", "story", "task"):
            print(TYPE_LABELS[t] + "：")
            for fid, label, kind, hint in REQUIRED[t]:
                print("  - %s（%s）—— %s" % (label, fid, hint))
            print("")
        print("Bug（缺陷）· 生产缺陷处理空间 36495762（手册第 7 章）：")
        for fid, label, kind, hint in REQUIRED["bug"]:
            print("  - %s（%s）—— %s" % (label, fid, hint))
        print("")
        print("Bug（缺陷）· 需求池空间 32496738（手册第 4 章，与上面不同）：")
        for fid, label, kind, hint in REQUIRED_BUG_POOL["bug"]:
            print("  - %s（%s）—— %s" % (label, fid, hint))
        print("")
        print("父需求层级铁律（父需求只能是上一级，禁止同级 / 越级）：")
        print("  - Epic     → 无父需求（顶层）")
        print("  - Feature  → 父需求必须是 Epic（史诗故事）")
        print("  - Story    → 父需求必须是 Feature（特性）　✗ 不允许 Story 挂 Story")
        print("  - Task     → 父需求必须是 Story（需求）　　✗ 不允许 Task 挂 Task")
        print("  - Bug（缺陷）→ 无父需求层级要求（独立空间 36495762，不走层级校验）")
        print("  · 调用方可额外传 parent_type（支持 epic/feature/story/task、中文名或 workitem_type_id），")
        print("    脚本会校验；不传则只能给「请自行核实」提示（离线无法查父级类型）。")
        return 0

    try:
        if args.items_file:
            raw = sys.stdin.read() if args.items_file == "-" else open(args.items_file, encoding="utf-8").read()
            data = json.loads(raw)
        elif args.data:
            obj = json.loads(args.data)
            if args.type and isinstance(obj, dict) and not obj.get("type"):
                obj["type"] = args.type
            data = obj
        else:
            print("需要 --items-file 或 --data（详见 --help）", file=sys.stderr)
            return 2
    except json.JSONDecodeError as e:
        print("输入不是合法 JSON：%s" % e, file=sys.stderr)
        return 2

    items = data if isinstance(data, list) else [data]
    if not items:
        print("待创建列表为空", file=sys.stderr)
        return 2

    results = [validate_one(it, strict_template=args.strict_template,
                            strict_enum=args.strict_enum) for it in items]
    for i, r in enumerate(results, 1):
        r["index"] = i

    report = {
        "ok": all(r["ok"] for r in results),
        "total": len(results),
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "warnings": sum(len(r["warnings"]) for r in results),
        "results": results,
    }

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
