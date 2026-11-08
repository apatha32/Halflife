from datetime import date

from halflife.alerts import message


def test_message_lists_riskiest_first_in_plain_words():
    alerts = [
        {"drive_id": "B", "rank": 40, "kind": "rank_jump", "prev_rank": 1200},
        {"drive_id": "A", "rank": 3, "kind": "entered_top_k", "prev_rank": 61},
    ]
    assert message("Acme Storage", date(2026, 9, 30), 50, alerts) == (
        "Halflife: 2 new alerts for Acme Storage on 2026-09-30\n"
        "- A: rank 3, entered the top 50\n"
        "- B: rank 40, rose from rank 1,200"
    )
