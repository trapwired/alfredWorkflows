import unittest

from dg.loops import loop_from_note, rows_for_loops


def loop(path, **fields):
    return loop_from_note(path, fields)


class OpenLoopRows(unittest.TestCase):
    def test_lists_only_open_loops_grouped_by_status_then_prio_descending(self):
        loops = [
            loop("Loops/Geparkt.md", status="geparkt", prio="99"),
            loop("Loops/Niedrig.md", status="aktiv", prio="10"),
            loop("Loops/Fertig.md", status="erledigt", prio="80"),
            loop("Loops/Hoch.md", status="aktiv", prio="90"),
            loop("Loops/Wartet.md", status="wartet", prio="50"),
        ]

        titles = [item["title"] for item in rows_for_loops(loops)]

        self.assertEqual(titles, ["Hoch", "Niedrig", "Wartet", "Geparkt"])

    def test_loop_without_prio_sorts_after_prioritised_ones(self):
        loops = [loop("Loops/Ohne.md", status="aktiv", prio=""), loop("Loops/Mit.md", status="aktiv", prio="0")]

        titles = [item["title"] for item in rows_for_loops(loops)]

        self.assertEqual(titles, ["Mit", "Ohne"])

    def test_enter_opens_warp_tab_and_cmd_opens_the_note(self):
        item = rows_for_loops(
            [loop("Loops/Alfred Workflows.md", status="aktiv", prio="40", warp="warp://tab_config/loop_alfred_workflows")]
        )[0]

        self.assertEqual(item["arg"], "warp://tab_config/loop_alfred_workflows")
        self.assertEqual(item["mods"]["cmd"]["arg"], "obsidian://open?vault=notes-dg&file=Loops%2FAlfred%20Workflows")

    def test_story_loop_shows_key_and_title_without_note_suffix(self):
        item = rows_for_loops([loop("Jira/OPA-52654  Aufräumstory - Jira.md", status="wartet", wartet_auf="Pascal")])[0]

        self.assertEqual(item["title"], "OPA-52654  Aufräumstory")
        self.assertIn("wartet auf Pascal", item["subtitle"])
        self.assertIn("Jira%2FOPA-52654", item["mods"]["cmd"]["arg"])

    def test_loop_without_warp_link_opens_the_note_and_says_so(self):
        item = rows_for_loops([loop("Loops/Neu.md", status="aktiv", frist="2026-12-01")])[0]

        self.assertTrue(item["arg"].startswith("obsidian://open?vault=notes-dg&file=Loops%2FNeu"))
        self.assertIn("kein Warp-Tab", item["subtitle"])
        self.assertIn("Frist 2026-12-01", item["subtitle"])

    def test_no_open_loop_gives_a_hint_instead_of_an_empty_list(self):
        rows = rows_for_loops([loop("Loops/Fertig.md", status="erledigt")])

        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["valid"])


if __name__ == "__main__":
    unittest.main()
