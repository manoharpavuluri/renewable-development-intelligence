"""
Layer 4 — graph-topology regression test.

Guards against the exact class of bug CLAUDE_HANDOFF.md
documented: a conditional-edge branch referencing a node that was
never registered. Every branch target used by
build_investigation_graph must resolve to a registered node (or
END) at compile time.
"""

from __future__ import annotations

from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
)


EXPECTED_BRANCH_MAPS = {
    "route_after_validation": {
        "select": "select_next_investigation",
        "end": "__end__",
    },
    "route_after_selection": {
        "plan": "plan_project_investigation",
        "capability": "check_capability",
        "end": "__end__",
    },
    "route_after_project_planning": {
        "capability": "check_capability",
        "end": "__end__",
    },
    "route_capability": {
        "execute": "execute_capability",
        "blocked": "capability_blocked",
    },
    "route_after_assessment": {
        "follow_up": "plan_follow_up",
        "domain_complete": "record_domain_outcome",
        "end": "__end__",
    },
}


def test_graph_compiles():

    build_investigation_graph()


def test_every_branch_target_resolves_to_a_registered_node():

    graph = build_investigation_graph()

    node_names = set(graph.get_graph().nodes.keys())

    for route_name, branch_map in EXPECTED_BRANCH_MAPS.items():

        for label, target in branch_map.items():

            assert target in node_names, (
                f"{route_name} -> {label!r} -> {target!r} does "
                "not resolve to a registered node."
            )
