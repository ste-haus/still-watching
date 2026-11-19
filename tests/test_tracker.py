from conftest import DEVICE, MOVIE, SERIES_B, SESSION


SESSION_ON_DEVICE = f"{SESSION}-{DEVICE}"
SHORT_BREAK_MINUTES = 5
LONG_BREAK_MINUTES = 60
SKIM_SECONDS = 20


def test_episode_counts_only_after_start_delay(harness):
    harness.start("e1")
    harness.wait(59)
    assert harness.count() == 0

    harness.wait(1)
    assert harness.count() == 1


def test_back_to_back_run_asks_at_start_of_next_episode(harness):
    for episode in ("e1", "e2", "e3", "e4"):
        harness.watch(episode)

    assert harness.count() == 4
    assert harness.asked == []

    harness.start("e5")
    harness.wait(59)
    assert harness.asked == []

    harness.wait(1)
    assert harness.asked == [SESSION_ON_DEVICE]


def test_asked_episode_starts_a_new_run(harness):
    for episode in ("e1", "e2", "e3", "e4"):
        harness.watch(episode)

    harness.watch("e5")
    assert harness.count() == 1
    assert len(harness.asked) == 1

    for episode in ("e6", "e7", "e8"):
        harness.watch(episode)

    assert harness.count() == 4
    assert len(harness.asked) == 1

    harness.start("e9")
    harness.wait(60)
    assert len(harness.asked) == 2


def test_resuming_the_paused_episode_does_not_count_again(harness):
    for episode in ("e1", "e2", "e3", "e4"):
        harness.watch(episode)

    harness.start("e5")
    harness.wait(60)
    assert harness.count() == 1

    harness.stop("e5")
    harness.wait_minutes(SHORT_BREAK_MINUTES)
    harness.start("e5")
    harness.wait(60)
    assert harness.count() == 1
    assert len(harness.asked) == 1


def test_short_breaks_keep_the_run(harness):
    for episode in ("e1", "e2", "e3", "e4"):
        harness.watch(episode)
        harness.wait_minutes(SHORT_BREAK_MINUTES)

    assert harness.count() == 4


def test_break_longer_than_gap_restarts_the_run(harness):
    harness.watch("e1")
    harness.wait_minutes(LONG_BREAK_MINUTES)
    harness.watch("e2")
    harness.wait_minutes(LONG_BREAK_MINUTES)
    harness.watch("e3")

    assert harness.count() == 1


def test_gap_is_measured_from_the_end_of_the_previous_episode(harness):
    harness.start("e1")
    harness.wait_minutes(2)
    harness.stop("e1")
    harness.wait_minutes(9)

    harness.start("e2")
    harness.wait(60)
    assert harness.count() == 2


def test_skimming_past_an_episode_does_not_count_it(harness):
    harness.watch("e1")
    harness.start("e2")
    harness.wait(SKIM_SECONDS)
    harness.start("e3")
    harness.wait(60)

    assert harness.count() == 2


def test_stopping_within_start_delay_does_not_count(harness):
    harness.start("e1")
    harness.wait(SKIM_SECONDS)
    harness.stop("e1")
    harness.wait(60)

    assert harness.count() == 0


def test_different_series_restarts_the_run(harness):
    harness.watch("e1")
    harness.watch("e2")
    harness.watch("b1", series_id=SERIES_B)

    assert harness.count() == 1


def test_movie_restarts_the_run(harness):
    harness.watch("e1")
    harness.watch("e2")
    harness.watch("m1", item_type=MOVIE)
    harness.watch("e3")

    assert harness.count() == 1


def test_missing_stop_falls_back_to_runtime(harness):
    harness.start("e1")
    harness.wait_minutes(3 * LONG_BREAK_MINUTES)

    harness.start("e2")
    harness.wait(60)
    assert harness.count() == 1


def test_missing_stop_with_autoplay_keeps_the_run(harness):
    harness.start("e1")
    harness.wait_minutes(23)

    harness.start("e2")
    harness.wait(60)
    assert harness.count() == 2


def test_devices_are_tracked_separately(harness):
    harness.watch("e1")
    harness.watch("e2")
    harness.watch("e1", device="phone")

    assert harness.count() == 2
    assert harness.count(device="phone") == 1
