"""The simulated residents of `pnpm eval:galtea`, without Galtea or a model: scenarios, the call, the verdict."""

import csv
import io
import json

from app import simulated_residents as sim
from app.models import TriageStatus
from app.providers import galtea


def _scenario(key: str) -> sim.Scenario:
    return next(s for s in sim.SCENARIOS if s.key == key)


def _tool_call(name: str, arguments: dict, call_id: str = "c1") -> dict:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


def test_the_scenarios_cover_the_adversarial_residents_with_a_valid_outcome_each() -> None:
    keys = [s.key for s in sim.SCENARIOS]

    assert len(keys) == len(set(keys))
    assert {"prank-caller", "confused-elderly", "panicked-parent", "refuses-to-leave", "wheelchair-user", "wrong-address"} <= set(keys)
    for scenario in sim.SCENARIOS:
        assert scenario.accepted and scenario.accepted <= {TriageStatus.EVACUATING, TriageStatus.NEEDS_RESCUE, TriageStatus.NO_ANSWER}
        assert ":" not in scenario.key


def test_the_behavior_file_has_galteas_columns_and_maps_back_to_each_scenario() -> None:
    rows = list(csv.DictReader(io.StringIO(sim.behavior_csv())))

    assert list(rows[0]) == ["goal", "user_persona", "input", "stopping_criterias", "max_iterations", "scenario"]
    assert [sim.scenario_key(row["scenario"]) for row in rows] == [s.key for s in sim.SCENARIOS]
    assert all(row["max_iterations"] == str(sim.MAX_TURNS) and "|" in row["stopping_criterias"] for row in rows)


def test_the_dataset_name_changes_with_the_scenarios() -> None:
    fewer = sim.SCENARIOS[:2]

    assert sim.dataset_name() == sim.dataset_name()
    assert sim.dataset_name(fewer) != sim.dataset_name()


def test_the_agent_opens_with_its_greeting_and_its_filled_in_prompt() -> None:
    call = sim.ResidentCall(_scenario("wheelchair-user"), complete=lambda messages: {"content": "unused"})

    assert call.reply(None) == "Hola, buenas. ¿Hablo con Pilar Romero?"
    assert "Pilar Romero" in call.messages[0]["content"] and "{{" not in call.messages[0]["content"]


def test_the_agent_records_the_report_then_says_goodbye_and_hangs_up() -> None:
    answers = iter(
        [
            {"content": "", "tool_calls": [_tool_call("report_status", {"status": "needs_rescue", "people": 1})]},
            {"content": "He avisado a la coordinación.", "tool_calls": [_tool_call("end_call", {}, "c2")]},
        ]
    )
    call = sim.ResidentCall(_scenario("wheelchair-user"), complete=lambda messages: next(answers))
    call.reply(None)

    said = call.reply("Estoy sola y no puedo salir.")

    assert said == "He avisado a la coordinación."
    assert call.reports == [{"status": "needs_rescue", "people": 1}]
    assert call.ended and call.reply("¿Hola?") == ""
    assert [m["role"] for m in call.messages[-4:]] == ["assistant", "tool", "assistant", "tool"]
    assert "[report_status" in sim.transcript(call.messages)


def test_a_silent_hang_up_still_shows_in_the_transcript() -> None:
    call = sim.ResidentCall(_scenario("prank-caller"), complete=lambda messages: {"tool_calls": [_tool_call("end_call", {})]})

    assert call.reply("Soy un pirata.") == sim.HANG_UP


def test_the_verdict_reads_the_last_report() -> None:
    scenario = _scenario("refuses-to-leave")

    assert sim.judge(scenario, []).passed is False
    assert sim.judge(scenario, [{"status": "evacuating"}, {"status": "needs_rescue"}]).passed is True
    failed = sim.judge(scenario, [{"status": "needs_rescue"}, {"status": "evacuating"}])
    assert failed.passed is False and failed.status == "evacuating" and "needs_rescue" in failed.detail


def test_galtea_is_off_without_a_key(monkeypatch) -> None:
    from dataclasses import replace

    monkeypatch.setattr(galtea, "settings", replace(galtea.settings, galtea_api_key=""))

    assert galtea.configured() is False
    try:
        galtea.connect()
    except galtea.GalteaUnavailable as error:
        assert "GALTEA_API_KEY" in str(error)
    else:
        raise AssertionError("connect() must refuse without a key")
