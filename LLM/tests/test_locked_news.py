from __future__ import annotations

import pytest

from LLM.locked_news import lock_standalone_news, restore_locked_news


def test_locks_only_space_delimited_news_and_restores_it() -> None:
    locked = lock_standalone_news("오늘 news 보도 news입니다. news ")

    assert locked.text == "오늘 <LOCK_0001> 보도 news입니다. <LOCK_0002> "
    assert restore_locked_news(locked.text, locked) == "오늘 news 보도 news입니다. news "


def test_lock_indices_do_not_collide_with_existing_lock_tokens() -> None:
    locked = lock_standalone_news("<LOCK_0001> news ")

    assert locked.text == "<LOCK_0001> <LOCK_0002> "


def test_restore_rejects_missing_or_duplicated_news_lock() -> None:
    locked = lock_standalone_news(" news ")

    with pytest.raises(ValueError, match="exactly once"):
        restore_locked_news("뉴스", locked)
    with pytest.raises(ValueError, match="exactly once"):
        restore_locked_news("<LOCK_0001> <LOCK_0001>", locked)
