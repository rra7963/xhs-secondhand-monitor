import time
import random
import os
import re
from datetime import datetime, timedelta
from DrissionPage import ChromiumPage, ChromiumOptions
from plyer import notification

# 配置区，这个可以根据自己需求改动检索关键词
# 包含一个 TARGET + 一个 ACTION
TARGET_WORDS = ["电视", "显示器", "机", "投影"]
ACTION_WORDS = ["出", "自用", "二手", "搬家", "闲置", "处理", "回血", "不收"]
EXCLUDE_WORDS = ["求购", "想买", "想收", "蹲一个", "谁有", "有没有", "交流群", "求推荐"]

CHECK_INTERVAL = (600, 900)
USER_DATA_PATH = os.path.join(os.getcwd(), 'xhs_profile')
RESULT_FILE = "最新排序_实时监控.txt"



def save_to_notepad(title, note_id, post_date):
    url = f"https://www.xiaohongshu.com/explore/{note_id}"
    now = datetime.now().strftime('%m-%d %H:%M')
    clean_title = title.replace('\n', ' ').strip()[:50]
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"【发现】:{now} | 【日期】:{post_date} | {clean_title}\n")
        f.write(f"【链接】:{url}\n")
        f.write("-" * 60 + "\n")
    print(f"✨ >>> [成功命中并记录] {clean_title}")


def is_within_30_days(time_str):
    if not time_str or time_str == "未知": return True
    if any(x in time_str for x in ["刚刚", "小时", "分钟", "昨天", "天前"]):
        return True
    try:
        current_year = datetime.now().year
        t_str = f"{current_year}-{time_str}" if len(time_str) <= 5 else time_str
        target_date = datetime.strptime(t_str, '%Y-%m-%d')
        return (datetime.now() - target_date).days <= 30
    except:
        return True


def force_latest_sort(page):
    """切换最新"""
    print("  ⚙️ 正在执行【强制锁定最新排序】...")
    try:
        # 1. 尝试点击“筛选”
        for _ in range(3):
            btn = page.ele('text=筛选', timeout=2)
            if btn:
                btn.click(by_js=True)
                page.wait(1)
                if page.ele('text=排序依据', timeout=1): break  # 菜单开了就跳出

        # 2. 暴力点击所有叫“最新”的元素
        newest_btns = page.eles('text=最新')
        if newest_btns:
            for n_btn in newest_btns:
                try:
                    n_btn.click(by_js=True)  # 用JS强行穿透点击
                except:
                    continue
            print("  ✅ 已发出【最新】排序指令")
            page.wait(3, 4)
            return True
    except Exception as e:
        print(f"  ❌ 切换过程出错: {e}")
    return False


def monitor():
    co = ChromiumOptions()
    co.set_user_data_path(USER_DATA_PATH)
    page = ChromiumPage(co)

    seen_ids = set()
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            seen_ids = set(re.findall(r'explore/(\w+)', f.read()))

    print(f"🚀 锁定最新监控启动！专注首屏 12 条...")

    while True:
        try:
            for kw in ["出电视", "自用电视", "二手电视"]:
                print(f"\n📡 [{datetime.now().strftime('%H:%M:%S')}] 扫描: {kw}")
                url = f'https://www.xiaohongshu.com/search_result?keyword={kw}&source=web_search_result_notes&sort=new'
                page.get(url)
                page.wait(2, 3)

                # 必须切换到最新
                force_latest_sort(page)

                items = page.eles('.note-item')
                # 严格限制：只看前 12 个，确保是“最新”标签下的第一页
                print(f"📊 正在判定首屏 {len(items[:12])} 个帖子...")

                for index, item in enumerate(items[:12]):
                    try:
                        link_node = item.ele('tag:a', timeout=1)
                        if not link_node: continue
                        note_id = link_node.attr('href').split('/')[-1]

                        if note_id in seen_ids:
                            print(f"  [{index + 1}] 跳过 (已记录)")
                            continue

                        full_text = item.text.replace('\n', ' ')
                        print(f"  [{index + 1}] 检查: {full_text[:12]}...", end=" -> ")

                        # 组合逻辑判定
                        has_target = any(t in full_text for t in TARGET_WORDS)
                        has_action = any(a in full_text for a in ACTION_WORDS)

                        if has_target and has_action:
                            if any(word in full_text for word in EXCLUDE_WORDS):
                                print("跳过 (排除词)")
                                seen_ids.add(note_id)
                                continue

                            print("🎯 命中，确认日期...", end="")
                            page.scroll.to_see(item)
                            item.click(by_js=True)
                            page.wait(2, 3)

                            date_ele = page.ele('.date', timeout=2) or page.ele('.bottom-container', timeout=1)
                            raw_date = date_ele.text.replace("发布于 ", "").replace("编辑于 ", "").split(" ")[
                                0] if date_ele else "未知"

                            if is_within_30_days(raw_date):
                                lines = [l.strip() for l in full_text.split(' ') if l.strip()]
                                save_to_notepad(lines[0] if lines else "电视", note_id, raw_date)
                                notification.notify(title="发现最新电视", message=full_text[:20])
                            else:
                                print(f" -> ⏩ 过期({raw_date})")

                            seen_ids.add(note_id)
                            # 关闭详情
                            page.actions.move_to((10, 10)).click()
                            page.wait(1)
                        else:
                            print("跳过 (不含关键词)")

                    except Exception:
                        page.actions.move_to((10, 10)).click()
                        continue

            sleep_t = random.randint(CHECK_INTERVAL[0], CHECK_INTERVAL[1])
            print(f"\n💤 扫荡结束。下轮预计: {(datetime.now() + timedelta(seconds=sleep_t)).strftime('%H:%M:%S')}")
            time.sleep(sleep_t)

        except Exception as e:
            print(f"❌ 系统异常: {e}")
            time.sleep(60)


if __name__ == "__main__":
    monitor()
