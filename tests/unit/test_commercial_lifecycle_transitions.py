from app.models.commercial import validate_engagement_transition


def test_engagement_transitions_follow_persisted_enum():
    assert validate_engagement_transition("IDENTIFIED", "QUOTED")
    assert validate_engagement_transition("QUOTED", "CONFIRMED")
    assert validate_engagement_transition("CONFIRMED", "IN_PROGRESS")
    assert validate_engagement_transition("IN_PROGRESS", "COMPLETED")


def test_engagement_terminal_states_cannot_advance():
    assert not validate_engagement_transition("COMPLETED", "IDENTIFIED")
    assert not validate_engagement_transition("CANCELLED", "IDENTIFIED")


def test_non_enum_legacy_states_are_rejected():
    assert not validate_engagement_transition("CONFIRMED", "STARTED")
    assert not validate_engagement_transition("QUOTED", "REJECTED")
    assert not validate_engagement_transition("UNKNOWN", "COMPLETED")


def test_transition_validator_accepts_enum_instances_and_cancellation():
    from app.models.enums import EngagementStatus

    assert validate_engagement_transition(
        EngagementStatus.IDENTIFIED, EngagementStatus.CANCELLED
    )
    assert not validate_engagement_transition(
        EngagementStatus.IDENTIFIED, EngagementStatus.IDENTIFIED
    )
