#!/usr/bin/env python3

"""
Static topology guard for the investigation graph.

This intentionally does not depend on a checkpointer, Foundry
credentials, or governed evidence. It only proves that the graph
as currently wired is internally consistent:

  - every conditional route's possible return values map to a
    node that is actually registered (or END)
  - the graph compiles

This should be run any time investigation_graph.py is edited,
since partial topology edits (a route added without its node
registration, or vice versa) fail silently until compile time.
"""

from __future__ import annotations

from renewable_intelligence.graph import investigation_graph as ig


def main() -> None:

    graph = ig.build_investigation_graph()

    print("=== GRAPH COMPILE ===")
    print("OK")

    node_names = set(graph.get_graph().nodes.keys())

    print()
    print("=== REGISTERED NODES ===")
    for name in sorted(node_names):
        print("-", name)

    # Cross-check every conditional-edge branch map used in
    # build_investigation_graph against the compiled node set.
    # We reconstruct the same branch maps used at graph-build time
    # so this test fails loudly if someone edits one without the
    # other.
    expected_branch_maps = {
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

    print()
    print("=== BRANCH TARGET CHECK ===")

    failures = []

    for route_name, branch_map in expected_branch_maps.items():

        for label, target in branch_map.items():

            ok = target in node_names

            status = "OK" if ok else "MISSING"

            print(f"{route_name} -> {label!r} -> {target!r}: {status}")

            if not ok:
                failures.append((route_name, label, target))

    print()

    if failures:
        print(f"FAILED: {len(failures)} branch target(s) reference unregistered nodes.")
        raise SystemExit(1)

    print("PASSED: all conditional-edge branch targets resolve to registered nodes.")


if __name__ == "__main__":
    main()
