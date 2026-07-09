"""
接口压力测试脚本
目标：验证限流 QPS=10、总额度 500 是否生效
主要观察额度耗尽时机与响应状态码

用法：python load_test_quota.py
"""

import time
import json
import threading
import requests
from datetime import datetime
from collections import defaultdict

# ─── 配置区 ────────────────────────────────────────────────────────────────

TARGET_QPS   = 10    # 每秒最多发出的请求数
TOTAL_QUOTA  = 500   # 总请求次数上限（验证额度）
TIMEOUT_SEC  = 15    # 单次请求超时秒数

TOKEN = (
    "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
    "eyJleHAiOjE3ODU1NjM5NzUsImNpZCI6MywidWlkIjoiSlBONDkiLCJqdGkiOiJhYjdhZWM4MiJ9."
    "uCeddx-myU6cP6Wo-fBFGA1-HytWu7gptg1LUkfSc3Q"
)

# 列表搜索接口
SEARCH_URL = "https://main-api.hubbuyer.com/open_api/v1/product/search"
SEARCH_HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
}
SEARCH_BODY = {
    "keyword": "衣服",
    "keyword_language": "ja",
    "page": 2,
    "page_size": 20,
    "price_min": 10,
    "price_max": 50,
    "ship_time": "24h",
    "include_detail": False,
    "certified_factory": False,
    "one_piece_dropship": False,
    "new_arrival_7d": False,
    "selection_1688": False,
    "sort": "sales_desc",
}

# 详情接口
DETAIL_URL = "https://main-api.hubbuyer.com/open_api/v1/product/detail"
DETAIL_HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json; charset=utf-8",
}
DETAIL_BODY = {
    "offer_id": "815779582773",
    "response_language": "ja",
    "include_sku": True,
    "include_html_detail": False,
}

# 本次压测使用的接口（两个共用同一个配额，用列表页打满额度）
TEST_URL     = SEARCH_URL
TEST_HEADERS = SEARCH_HEADERS
TEST_BODY    = SEARCH_BODY

# ─── 统计容器 ───────────────────────────────────────────────────────────────

lock           = threading.Lock()
results        = []           # (seq, status_code, elapsed_ms, ts, resp_snippet)
status_counter = defaultdict(int)
first_quota_exhausted_at = None   # 首次出现配额耗尽响应的序号

# ─── 单次请求 ───────────────────────────────────────────────────────────────

def do_request(seq: int):
    global first_quota_exhausted_at
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    try:
        t0 = time.perf_counter()
        resp = requests.post(
            TEST_URL,
            headers=TEST_HEADERS,
            json=TEST_BODY,
            timeout=TIMEOUT_SEC,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        code = resp.status_code

        # 尝试解析 JSON 摘要
        try:
            body = resp.json()
            snippet = json.dumps(body, ensure_ascii=False)[:120]
        except Exception:
            snippet = resp.text[:120]

    except requests.exceptions.Timeout:
        elapsed = TIMEOUT_SEC * 1000
        code, snippet = 0, "TIMEOUT"
    except Exception as e:
        elapsed = 0
        code, snippet = -1, str(e)[:120]

    with lock:
        results.append((seq, code, elapsed, ts, snippet))
        status_counter[code] += 1
        # 检测配额耗尽：常见返回码 429 / 403 / 200-with-error
        if first_quota_exhausted_at is None:
            is_quota_err = (
                code == 429
                or (code == 200 and ("quota" in snippet.lower()
                                     or "limit" in snippet.lower()
                                     or "超出" in snippet
                                     or "额度" in snippet
                                     or "rate" in snippet.lower()))
                or (code == 403 and "quota" in snippet.lower())
            )
            if is_quota_err:
                first_quota_exhausted_at = seq
                print(f"\n!!! [seq={seq}] 疑似额度耗尽 → HTTP {code}  {snippet[:80]}")

# ─── 令牌桶限速器 ───────────────────────────────────────────────────────────

class TokenBucket:
    def __init__(self, rate: int):
        self.rate     = rate        # tokens/sec
        self.tokens   = rate
        self.last_ts  = time.monotonic()
        self._lock    = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_ts
                self.tokens += elapsed * self.rate
                if self.tokens > self.rate:
                    self.tokens = self.rate
                self.last_ts = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
            time.sleep(0.01)

# ─── 主流程 ─────────────────────────────────────────────────────────────────

def main():
    bucket = TokenBucket(TARGET_QPS)
    threads = []

    print(f"=== 压测开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"目标：{TEST_URL}")
    print(f"QPS 上限={TARGET_QPS}  总请求数={TOTAL_QUOTA}")
    print("-" * 60)

    start = time.perf_counter()

    for seq in range(1, TOTAL_QUOTA + 1):
        bucket.acquire()               # 限速
        t = threading.Thread(target=do_request, args=(seq,), daemon=True)
        threads.append(t)
        t.start()

        # 每 50 条打印一次进度
        if seq % 50 == 0:
            with lock:
                done = len(results)
                dist = dict(sorted(status_counter.items()))
            print(f"  已发 {seq:>4}  已收 {done:>4}  状态分布: {dist}")

    # 等待所有线程完成
    for t in threads:
        t.join(timeout=TIMEOUT_SEC + 5)

    total_time = time.perf_counter() - start

    # ─── 汇总报告 ─────────────────────────────────────────────────────────

    print("\n" + "=" * 60)
    print(f"=== 压测完成  耗时 {total_time:.1f}s ===")
    print(f"总发送: {TOTAL_QUOTA}  总收到: {len(results)}")
    print(f"实际 QPS: {TOTAL_QUOTA / total_time:.2f}")
    print()
    print("[ HTTP 状态码分布 ]")
    for code, cnt in sorted(status_counter.items()):
        label = {
            200: "OK",
            429: "Too Many Requests (限流/配额)",
            403: "Forbidden",
            401: "Unauthorized",
            0:   "TIMEOUT",
            -1:  "连接异常",
        }.get(code, "")
        bar = "█" * min(cnt, 50)
        print(f"  {str(code):>5}  {cnt:>5}次  {bar}  {label}")

    print()
    if first_quota_exhausted_at:
        print(f"[重要] 首次疑似额度耗尽 → 第 {first_quota_exhausted_at} 条请求")
        print(f"       说明：在发出 {first_quota_exhausted_at} 次请求后配额触发")
    else:
        print("[重要] 未检测到明确的配额耗尽响应（500 条均未触发）")

    # 延迟统计（仅 HTTP 200）
    ok_latencies = [r[2] for r in results if r[1] == 200]
    if ok_latencies:
        ok_latencies.sort()
        n = len(ok_latencies)
        print()
        print(f"[ 响应延迟（仅 200 OK，共 {n} 条）]")
        print(f"  Min   : {ok_latencies[0]} ms")
        print(f"  P50   : {ok_latencies[n // 2]} ms")
        print(f"  P90   : {ok_latencies[int(n * 0.9)]} ms")
        print(f"  P99   : {ok_latencies[int(n * 0.99)]} ms")
        print(f"  Max   : {ok_latencies[-1]} ms")

    # 输出前 5 条异常样本
    errors = [(r[0], r[1], r[4]) for r in results if r[1] not in (200,)]
    if errors:
        print()
        print(f"[ 异常样本（前 5 条，共 {len(errors)} 条）]")
        for seq, code, snippet in errors[:5]:
            print(f"  seq={seq:>4}  HTTP {code}  {snippet[:100]}")

    print("=" * 60)

    # 写结果到文件
    out_path = f"load_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_sent": TOTAL_QUOTA,
                "total_received": len(results),
                "duration_sec": round(total_time, 2),
                "actual_qps": round(TOTAL_QUOTA / total_time, 2),
                "status_distribution": dict(status_counter),
                "first_quota_exhausted_at_seq": first_quota_exhausted_at,
            },
            "records": [
                {"seq": r[0], "http_code": r[1], "elapsed_ms": r[2],
                 "time": r[3], "response_snippet": r[4]}
                for r in sorted(results, key=lambda x: x[0])
            ],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存 → {out_path}")


if __name__ == "__main__":
    main()
