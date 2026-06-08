```python
def _parse_minkabu_calendar(html: str):
    """
    みんかぶ経済指標カレンダーを
    HTMLテーブルから直接解析

    戻り値:
    [
        {
            event_date_jst,
            event_time_jst,
            country,
            event_name,
            forecast,
            actual,
            previous,
            importance_label,
            event_status,
        }
    ]
    """

    soup = BeautifulSoup(html, "html.parser")

    COUNTRY_MAP = {
        "日本": "JP",
        "米国": "US",
        "アメリカ": "US",
        "米": "US",
    }

    NO_RESULT_VALUES = {
        "",
        "-",
        "--",
        "---",
        "未定",
        "未発表",
        "N/A",
    }

    events = []

    current_date = None

    #
    # 日付見出しを取得
    #
    date_pattern = re.compile(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日"
    )

    #
    # テーブルを順番に走査
    #
    for table in soup.find_all("table"):

        #
        # テーブル直前に日付があるケース
        #
        prev_text = ""

        for tag in table.find_all_previous(limit=10):
            txt = _normalize_text(tag.get_text(" ", strip=True))

            if date_pattern.search(txt):
                prev_text = txt
                break

        if prev_text:
            current_date = _jp_date_to_iso(prev_text)

        rows = table.find_all("tr")

        for tr in rows:

            cols = [
                _normalize_text(td.get_text(" ", strip=True))
                for td in tr.find_all(["td", "th"])
            ]

            #
            # ヘッダー行除外
            #
            if len(cols) < 5:
                continue

            #
            # 時刻を探す
            #
            time_idx = None

            for idx, val in enumerate(cols):
                if re.match(r"^\d{2}:\d{2}$", val):
                    time_idx = idx
                    break

                if val == "未定":
                    time_idx = idx
                    break

            if time_idx is None:
                continue

            #
            # 想定構造
            #
            # 時刻
            # 国
            # 指標名
            # 重要度
            # 前回
            # 予想
            # 結果
            #
            try:

                event_time = cols[time_idx]

                country_raw = (
                    cols[time_idx + 1]
                    if len(cols) > time_idx + 1
                    else ""
                )

                event_name = (
                    cols[time_idx + 2]
                    if len(cols) > time_idx + 2
                    else ""
                )

                importance = (
                    cols[time_idx + 3]
                    if len(cols) > time_idx + 3
                    else ""
                )

                previous = (
                    cols[time_idx + 4]
                    if len(cols) > time_idx + 4
                    else ""
                )

                forecast = (
                    cols[time_idx + 5]
                    if len(cols) > time_idx + 5
                    else ""
                )

                actual = (
                    cols[time_idx + 6]
                    if len(cols) > time_idx + 6
                    else ""
                )

                #
                # 国フィルタ
                #
                if country_raw not in COUNTRY_MAP:
                    continue

                country = COUNTRY_MAP[country_raw]

                #
                # 日付が無い行は除外
                #
                if not current_date:
                    continue

                #
                # 発表済判定
                #
                event_status = (
                    "予定"
                    if actual in NO_RESULT_VALUES
                    else "結果"
                )

                events.append(
                    {
                        "event_date_jst": current_date,
                        "event_time_jst": event_time,
                        "country": country,
                        "event_name": event_name,
                        "forecast": forecast,
                        "actual": actual,
                        "previous": previous,
                        "importance_label": importance,
                        "event_status": event_status,
                    }
                )

            except Exception as e:
                print(
                    "[WARN] parse row error:",
                    e,
                    cols,
                )

    #
    # 重複除去
    #
    unique = {}

    for e in events:

        key = (
            e["event_date_jst"],
            e["event_time_jst"],
            e["country"],
            e["event_name"],
        )

        unique[key] = e

    events = list(unique.values())

    #
    # ソート
    #
    events.sort(
        key=lambda x: (
            x["event_date_jst"],
            x["event_time_jst"],
        )
    )

    print(
        f"[INFO] economic events parsed: {len(events)}"
    )

    return events
```
