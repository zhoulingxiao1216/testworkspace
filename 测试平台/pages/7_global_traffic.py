# -*- coding: utf-8 -*-
"""全球站访问量查询页：集中查看 1688 外访日志的近实时统计。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Sequence
from urllib.parse import unquote

import pandas as pd
import streamlit as st

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from modules.readonly_db import fetch_all

st.set_page_config(page_title="全球站访问量查询", page_icon="🌐", layout="wide")


def _apply_global_traffic_theme() -> None:
    """Keep this page aligned with the light Streamlit pages."""
    st.markdown(
        """
        <style>
        .stButton > button,
        .stButton > button:hover,
        .stButton > button:focus,
        .stButton > button:active {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #111827 !important;
            box-shadow: none !important;
        }

        .stButton > button p,
        .stButton > button:hover p,
        .stButton > button:focus p,
        .stButton > button:active p {
            color: #111827 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_apply_global_traffic_theme()


@dataclass(frozen=True)
class QuerySpec:
    """描述单个只读统计查询的展示信息与 SQL。"""

    title: str
    description: str
    sql: str
    limit: int = 500


# PyMySQL uses %-formatting for %s params, so literal LIKE wildcards are doubled.
PLATFORM_FILTER = """
(
  platform LIKE 'ali-1688-%%'
  OR platform LIKE '1688-%%'
)
""".strip()

FOCUS_PLATFORM_FILTER = "platform IN ('ali-1688-seller-search', 'ali-1688-detail')"
FOCUS_DETAIL_PATH = "path = '/api_ali/product/detail'"
USER_EMPTY_FILTER = "(user_id IS NULL OR user_id = '')"


def _normalize_sql(sql: str) -> str:
    """压缩 SQL 两端空白，避免展示和执行时出现多余空行。"""
    return sql.strip()


def _build_time_filter(mode: str, start_value: datetime | None, end_value: datetime | None) -> tuple[str, Sequence[object]]:
    """根据页面选择生成安全的时间条件与参数。"""
    if mode == "今日":
        return "date = CURDATE()", ()
    if mode == "昨日":
        return "date = DATE_SUB(CURDATE(), INTERVAL 1 DAY)", ()
    if mode == "自定义":
        if not start_value or not end_value:
            raise ValueError("自定义时间范围不能为空")
        if start_value >= end_value:
            raise ValueError("开始时间必须早于结束时间")
        return "created_at >= %s AND created_at < %s", (
            start_value.strftime("%Y-%m-%d %H:%M:%S"),
            end_value.strftime("%Y-%m-%d %H:%M:%S"),
        )
    return "created_at >= NOW() - INTERVAL 24 HOUR", ()


def _query(sql: str, params: Sequence[object] = (), limit: int = 500) -> pd.DataFrame:
    """执行只读 SQL 并转换为 DataFrame。"""
    rows = fetch_all(sql, params=params, limit=limit)
    return pd.DataFrame(rows)


def _decode_url_value(value: object) -> object:
    """解码 URL 参数中的中文，便于店铺名可读展示。"""
    if not isinstance(value, str) or "%" not in value:
        return value
    return unquote(value)


def _prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """对查询结果做展示层格式化，不改变 SQL 语义。"""
    if "seller_name" not in df.columns:
        return df
    display_df = df.copy()
    display_df["seller_name"] = display_df["seller_name"].map(_decode_url_value)
    return display_df


def _build_queries(time_where: str) -> dict[str, list[QuerySpec]]:
    """构造页面内全部访问量查询。"""
    return {
        "P0 核心看板": [
            QuerySpec(
                "1688 外访总量",
                "统计选定时间范围内所有 1688 相关平台调用量。",
                f"""
                SELECT COUNT(*) AS total_1688_calls
                FROM http_log
                WHERE {time_where}
                  AND {PLATFORM_FILTER}
                """,
                limit=1,
            ),
            QuerySpec(
                "各接口状态分布",
                "按 platform 与 status 聚合，快速判断失败或异常状态集中在哪些接口。",
                f"""
                SELECT platform, status, COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND {PLATFORM_FILTER}
                GROUP BY platform, status
                ORDER BY total DESC
                """,
                limit=1000,
            ),
            QuerySpec(
                "重点接口路径排行",
                "查看 seller-search 与 detail 两类平台下 path / url 的调用量排行。",
                f"""
                SELECT platform, path, url, COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND {FOCUS_PLATFORM_FILTER}
                GROUP BY platform, path, url
                ORDER BY total DESC
                """,
                limit=1000,
            ),
            QuerySpec(
                "按小时趋势",
                "按天、小时、platform、path 聚合，用于定位调用突增时段。",
                f"""
                SELECT
                  DATE(created_at) AS day,
                  HOUR(created_at) AS hour,
                  platform,
                  path,
                  COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND {FOCUS_PLATFORM_FILTER}
                  AND path IN ('/api_ali/product/detail', '/api_ali/product/recommend')
                GROUP BY day, hour, platform, path
                ORDER BY day, hour, total DESC
                """,
                limit=1000,
            ),
            QuerySpec(
                "数据时间范围校验",
                "确认当前统计命中的最早、最晚日志时间，排查时间字段或数据延迟问题。",
                f"""
                SELECT
                  MIN(created_at) AS min_created_at,
                  MAX(created_at) AS max_created_at,
                  COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND {PLATFORM_FILTER}
                """,
                limit=1,
            ),
        ],
        "P1 异常来源排查": [
            QuerySpec(
                "用户调用排行 Top50",
                "定位是否存在单用户高频调用。",
                f"""
                SELECT user_id, COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND platform = 'ali-1688-seller-search'
                  AND {FOCUS_DETAIL_PATH}
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 50
                """,
                limit=50,
            ),
            QuerySpec(
                "匿名请求 UA / Referer",
                "查看未登录或空用户请求的 user-agent 与 referer 分布。",
                f"""
                SELECT
                  JSON_UNQUOTE(JSON_EXTRACT(header, '$."user-agent"')) AS user_agent,
                  JSON_UNQUOTE(JSON_EXTRACT(header, '$."referer"')) AS referer,
                  COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND platform = 'ali-1688-seller-search'
                  AND {FOCUS_DETAIL_PATH}
                  AND {USER_EMPTY_FILTER}
                GROUP BY user_agent, referer
                ORDER BY total DESC
                LIMIT 50
                """,
                limit=50,
            ),
            QuerySpec(
                "匿名请求店铺名排行",
                "按可读店铺名统计匿名请求，优先取缓存店铺名，未命中时尝试取 referer 中的 sellerName。",
                f"""
                SELECT
                  COALESCE(
                    NULLIF(seller_info.name, ''),
                    NULLIF(parsed_log.referer_seller_name, ''),
                    '未缓存店铺名'
                  ) AS seller_name,
                  CASE
                    WHEN COALESCE(seller_info.name, '') <> '' THEN 'product_seller_info'
                    WHEN COALESCE(parsed_log.referer_seller_name, '') <> '' THEN 'referer.sellerName'
                    ELSE 'none'
                  END AS seller_name_source,
                  MIN(url) AS sample_url,
                  MIN(referer) AS sample_referer,
                  COUNT(DISTINCT seller_open_id) AS seller_count,
                  COUNT(*) AS total
                FROM (
                  SELECT
                    JSON_UNQUOTE(JSON_EXTRACT(
                      JSON_UNQUOTE(JSON_EXTRACT(param, '$.form_params.offerQueryParam')),
                      '$.sellerOpenId'
                    )) AS seller_open_id,
                    url,
                    JSON_UNQUOTE(JSON_EXTRACT(header, '$."referer"')) AS referer,
                    CASE
                      WHEN JSON_UNQUOTE(JSON_EXTRACT(header, '$."referer"')) LIKE '%%sellerName=%%'
                      THEN SUBSTRING_INDEX(
                        SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(header, '$."referer"')), 'sellerName=', -1),
                        '&',
                        1
                      )
                      ELSE ''
                    END AS referer_seller_name
                  FROM http_log
                  WHERE {time_where}
                    AND platform = 'ali-1688-seller-search'
                    AND {FOCUS_DETAIL_PATH}
                    AND {USER_EMPTY_FILTER}
                ) AS parsed_log
                LEFT JOIN product_seller_info AS seller_info
                  ON seller_info.open_id = parsed_log.seller_open_id
                 AND seller_info.type = 1688
                GROUP BY seller_name, seller_name_source
                ORDER BY total DESC
                LIMIT 50
                """,
                limit=50,
            ),
            QuerySpec(
                "UA 类型统计",
                "将匿名请求按 SSR 空 UA、bot UA 与其它来源分组。",
                f"""
                SELECT
                  CASE
                    WHEN JSON_UNQUOTE(JSON_EXTRACT(header, '$."user-agent"')) IS NULL THEN 'SSR_NULL_UA'
                    WHEN LOWER(JSON_UNQUOTE(JSON_EXTRACT(header, '$."user-agent"'))) LIKE '%%bot%%' THEN 'BOT_UA'
                    WHEN LOWER(JSON_UNQUOTE(JSON_EXTRACT(header, '$."user-agent"'))) LIKE '%%externalagent%%' THEN 'BOT_UA'
                    ELSE 'OTHER'
                  END AS ua_type,
                  COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND platform = 'ali-1688-seller-search'
                  AND {FOCUS_DETAIL_PATH}
                  AND {USER_EMPTY_FILTER}
                GROUP BY ua_type
                ORDER BY total DESC
                """,
                limit=20,
            ),
        ],
        "P2 深度排查": [
            QuerySpec(
                "seller-search Path 分布",
                "查看 ali-1688-seller-search 平台下所有 path 的访问量。",
                f"""
                SELECT path, COUNT(*) AS total
                FROM http_log
                WHERE {time_where}
                  AND platform = 'ali-1688-seller-search'
                GROUP BY path
                ORDER BY total DESC
                """,
                limit=500,
            ),
            QuerySpec(
                "店铺名 / 关键词 / 来源排行",
                "优先展示可读店铺名、关键词、path 与样本 url/referer；店铺名优先取缓存，未命中时尝试取 referer 中的 sellerName。",
                f"""
                SELECT
                  CASE
                    WHEN COALESCE(seller_open_id, '') <> '' AND COALESCE(keyword, '') = '' THEN '店铺商品查询'
                    WHEN COALESCE(keyword, '') <> '' THEN '关键词查询'
                    ELSE '未知查询'
                  END AS query_type,
                  COALESCE(
                    NULLIF(seller_info.name, ''),
                    NULLIF(parsed_log.referer_seller_name, ''),
                    '未缓存店铺名'
                  ) AS seller_name,
                  CASE
                    WHEN COALESCE(seller_info.name, '') <> '' THEN 'product_seller_info'
                    WHEN COALESCE(parsed_log.referer_seller_name, '') <> '' THEN 'referer.sellerName'
                    ELSE 'none'
                  END AS seller_name_source,
                  keyword,
                  path,
                  MIN(url) AS sample_url,
                  MIN(referer) AS sample_referer,
                  COUNT(DISTINCT seller_open_id) AS seller_count,
                  COUNT(*) AS total
                FROM (
                  SELECT
                    JSON_UNQUOTE(JSON_EXTRACT(
                      JSON_UNQUOTE(JSON_EXTRACT(param, '$.form_params.offerQueryParam')),
                      '$.sellerOpenId'
                    )) AS seller_open_id,
                    JSON_UNQUOTE(JSON_EXTRACT(
                      JSON_UNQUOTE(JSON_EXTRACT(param, '$.form_params.offerQueryParam')),
                      '$.keyword'
                    )) AS keyword,
                    path,
                    url,
                    JSON_UNQUOTE(JSON_EXTRACT(header, '$."referer"')) AS referer,
                    CASE
                      WHEN JSON_UNQUOTE(JSON_EXTRACT(header, '$."referer"')) LIKE '%%sellerName=%%'
                      THEN SUBSTRING_INDEX(
                        SUBSTRING_INDEX(JSON_UNQUOTE(JSON_EXTRACT(header, '$."referer"')), 'sellerName=', -1),
                        '&',
                        1
                      )
                      ELSE ''
                    END AS referer_seller_name
                  FROM http_log
                  WHERE {time_where}
                    AND platform = 'ali-1688-seller-search'
                ) AS parsed_log
                LEFT JOIN product_seller_info AS seller_info
                  ON seller_info.open_id = parsed_log.seller_open_id
                 AND seller_info.type = 1688
                GROUP BY query_type, seller_name, seller_name_source, keyword, path
                ORDER BY total DESC
                LIMIT 100
                """,
                limit=100,
            ),
        ],
    }


def _render_sql(spec: QuerySpec, time_params: Sequence[object]) -> None:
    """在折叠区展示 SQL 与当前参数，方便测试人员复核。"""
    with st.expander("查看 SQL", expanded=False):
        st.code(_normalize_sql(spec.sql), language="sql")
        if time_params:
            st.caption(f"时间参数：{', '.join(str(item) for item in time_params)}")


def _render_table(spec: QuerySpec, params: Sequence[object]) -> pd.DataFrame:
    """执行并渲染单个查询，返回结果 DataFrame 供上层做指标展示。"""
    try:
        df = _query(_normalize_sql(spec.sql), params=params, limit=spec.limit)
    except Exception as exc:  # noqa: BLE001
        st.error(f"{spec.title} 查询失败：{exc}")
        _render_sql(spec, params)
        return pd.DataFrame()

    _render_sql(spec, params)
    if df.empty:
        st.info("当前时间范围内没有查询结果。")
    else:
        st.dataframe(_prepare_display_df(df), use_container_width=True, hide_index=True)
    return df


def _render_hour_chart(df: pd.DataFrame) -> None:
    """按小时趋势结果渲染折线图。"""
    required = {"day", "hour", "platform", "path", "total"}
    if df.empty or not required.issubset(df.columns):
        return
    chart_df = df.copy()
    chart_df["hour_slot"] = (
        chart_df["day"].astype(str)
        + " "
        + chart_df["hour"].astype(int).astype(str).str.zfill(2)
        + ":00"
    )
    chart_df["series"] = chart_df["platform"].astype(str) + " | " + chart_df["path"].astype(str)
    pivot = (
        chart_df.pivot_table(index="hour_slot", columns="series", values="total", aggfunc="sum")
        .fillna(0)
        .sort_index()
    )
    st.line_chart(pivot, use_container_width=True)


def _render_p0_dashboard(specs: list[QuerySpec], params: Sequence[object]) -> None:
    """渲染默认核心看板。"""
    total_df = _render_table(specs[0], params)
    total_value = int(total_df.iloc[0]["total_1688_calls"]) if not total_df.empty else 0
    st.metric("1688 外访总量", f"{total_value:,}")

    status_col, path_col = st.columns([1, 1], gap="large")
    with status_col:
        st.subheader("各接口状态分布")
        st.caption(specs[1].description)
        _render_table(specs[1], params)
    with path_col:
        st.subheader("重点接口路径排行")
        st.caption(specs[2].description)
        _render_table(specs[2], params)

    trend_col, range_col = st.columns([1.35, 0.65], gap="large")
    with trend_col:
        st.subheader("按小时趋势")
        st.caption(specs[3].description)
        trend_df = _render_table(specs[3], params)
        _render_hour_chart(trend_df)
    with range_col:
        st.subheader("数据时间范围校验")
        st.caption(specs[4].description)
        _render_table(specs[4], params)


def _render_query_group(title: str, specs: list[QuerySpec], params: Sequence[object], expanded: bool = False) -> None:
    """渲染一组排查查询。"""
    with st.expander(title, expanded=expanded):
        for index, spec in enumerate(specs):
            if index:
                st.divider()
            st.subheader(spec.title)
            st.caption(spec.description)
            _render_table(spec, params)


def _flatten_queries(queries: dict[str, list[QuerySpec]]) -> list[tuple[str, QuerySpec]]:
    """按页面展示顺序展开查询分组。"""
    items: list[tuple[str, QuerySpec]] = []
    for category, specs in queries.items():
        for spec in specs:
            items.append((category, spec))
    return items


def _render_query_result(category: str, spec: QuerySpec, params: Sequence[object]) -> None:
    """执行并展示单个查询结果。"""
    st.markdown(f"#### {spec.title}")
    st.caption(f"{category} · {spec.description}")
    df = _render_table(spec, params)
    if spec.title == "1688 外访总量" and not df.empty and "total_1688_calls" in df.columns:
        st.metric("1688 外访总量", f"{int(df.iloc[0]['total_1688_calls']):,}")
    if spec.title == "按小时趋势":
        _render_hour_chart(df)


def _render_query_catalog(items: list[tuple[str, QuerySpec]]) -> int | None:
    """渲染左按钮、右名称的查询清单，返回当前选中的查询索引。"""
    selected_index = st.session_state.get("global_traffic_selected_query_index")
    st.markdown(f"### 查询清单（共 {len(items)} 项）")
    st.caption("左侧点击“查询”后仅执行当前这一条 SQL，右侧展示查询名称与用途。")
    for index, (category, spec) in enumerate(items, start=1):
        with st.container(border=True):
            action_col, name_col = st.columns([1.15, 8], gap="small")
            with action_col:
                st.write("")
                if st.button("查询", key=f"global_traffic_query_{index}", use_container_width=True):
                    selected_index = index - 1
                    st.session_state["global_traffic_selected_query_index"] = selected_index
            with name_col:
                st.markdown(f"**{index}. {spec.title}**")
                st.caption(f"{category} · {spec.description}")
    return selected_index


st.title("🌐 全球站访问量查询")
st.caption("集中查看 http_log 中 1688 外访接口的访问量、状态分布和异常来源。所有查询均复用平台只读数据库连接。")

default_start = datetime.now() - timedelta(hours=24)
default_end = datetime.now()

control_cols = st.columns([1, 1, 1], gap="large")
with control_cols[0]:
    time_mode = st.selectbox("时间范围", ["近24小时", "今日", "昨日", "自定义"], index=0)

custom_start = custom_end = None
if time_mode == "自定义":
    with control_cols[1]:
        start_date = st.date_input("开始日期", value=default_start.date())
        start_time = st.time_input("开始时间", value=time(default_start.hour, default_start.minute))
    with control_cols[2]:
        end_date = st.date_input("结束日期", value=default_end.date())
        end_time = st.time_input("结束时间", value=time(default_end.hour, default_end.minute))
    custom_start = datetime.combine(start_date, start_time)
    custom_end = datetime.combine(end_date, end_time)
else:
    with control_cols[1]:
        st.info("选择时间范围后，在下方清单左侧点击查询。")
    with control_cols[2]:
        st.caption("如需排查固定日期，可切换到今日 / 昨日 / 自定义。")

try:
    time_where_sql, time_params = _build_time_filter(time_mode, custom_start, custom_end)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

queries = _build_queries(time_where_sql)
query_items = _flatten_queries(queries)

catalog_col, result_col = st.columns([0.42, 0.58], gap="large")

with catalog_col:
    selected_query_index = _render_query_catalog(query_items)

with result_col:
    st.markdown("### 查询结果")
    with st.container(border=True):
        if selected_query_index is None:
            st.info("页面不会自动请求数据库，请点击左侧查询项的“查询”按钮。")
        else:
            selected_category, selected_spec = query_items[selected_query_index]
            st.cache_data.clear()
            _render_query_result(selected_category, selected_spec, time_params)
