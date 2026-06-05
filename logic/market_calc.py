from data.market_data import get_close_pair


def calc_change_pct(curr, prev):
    if curr is None or prev is None or prev == 0:
        return None
    return round((curr - prev) / prev * 100, 2)


def format_change(change):
    if change is None:
        return "N/A"
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.2f}%"


def build_rows(df, symbol_map):
    rows = []
    for label, symbol in symbol_map.items():
        curr, prev = get_close_pair(df, symbol)
        change = calc_change_pct(curr, prev)

        rows.append(
            {
                "label": label,
                "symbol": symbol,
                "current": curr,
                "previous": prev,
                "change_pct": change,
                "change_text": format_change(change),
            }
        )
    return rows


def summarize_sector_attention(sector_rows, top_n=3):
    valid = [r for r in sector_rows if r.get("change_pct") is not None]
    if not valid:
        return {"leaders": [], "laggards": []}

    leaders = sorted(valid, key=lambda x: x["change_pct"], reverse=True)[:top_n]
    laggards = sorted(valid, key=lambda x: x["change_pct"])[:top_n]

    return {
        "leaders": leaders,
        "laggards": laggards,
    }