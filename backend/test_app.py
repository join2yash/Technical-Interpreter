from app import interpret_text


TEST_TEXT = (
    "The payment processing job failed because the database connection timed out. "
    "The issue was detected by monitoring. "
    "The developer restarted the service and tested the job successfully."
)


def test_extracts_sentence_level_evidence():
    result = interpret_text(TEST_TEXT)

    assert result.extracted_information["issue"] == (
        "The payment processing job failed because the database connection timed out."
    )
    assert result.extracted_information["cause"] == (
        "The payment processing job failed because the database connection timed out."
    )
    assert result.extracted_information["identification"] == (
        "The issue was detected by monitoring."
    )
    assert result.extracted_information["people_involved"] == (
        "The developer restarted the service and tested the job successfully."
    )
    assert result.extracted_information["resolution"] == (
        "The developer restarted the service and tested the job successfully."
    )
    assert result.extracted_information["verification"] == (
        "The developer restarted the service and tested the job successfully."
    )
    assert result.missing_information == []
    assert result.clarification_questions == []


def test_missing_information_generates_targeted_questions():
    result = interpret_text("The payment processing job failed.")

    assert result.extracted_information["issue"] == "The payment processing job failed."
    assert "cause" in result.missing_information
    assert "identification" in result.missing_information
    assert "resolution" in result.missing_information
    assert "verification" in result.missing_information
    assert "What caused the issue?" in result.clarification_questions


def test_selected_sections_are_respected():
    result = interpret_text(
        "The payment processing job failed because the database connection timed out.",
        sections=["issue", "cause"],
    )

    assert set(result.extracted_information) == {"issue", "cause"}
    assert result.missing_information == []
