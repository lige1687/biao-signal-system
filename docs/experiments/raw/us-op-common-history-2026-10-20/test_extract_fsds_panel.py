import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
import importlib.util


MODULE_PATH = Path(__file__).with_name("extract_fsds_panel.py")
spec = importlib.util.spec_from_file_location("extract_fsds_panel", MODULE_PATH)
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)

TEST_ROOT = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/us-op-common-history-20261020/"
    "us-op-common-history-20261020-20261020T191922-92db83e55b32/result/fsds-panel-synthetic"
)


def tsv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def build_zip(changed_value=None):
    sub_fields = ["adsh", "cik", "name", "form", "period", "fy", "fp", "filed", "accepted", "instance", "prevrpt", "nciks", "aciks", "afs"]
    sub_rows = [
        {"adsh": "A", "cik": "100", "name": "One", "form": "10-K", "period": "20131231", "fy": "2013", "fp": "FY", "filed": "20140201", "accepted": "2014-02-01 10:00:00.0", "instance": "one.xml", "prevrpt": "0", "nciks": "1", "aciks": "", "afs": "LAF"},
        {"adsh": "B", "cik": "100", "name": "One", "form": "10-K/A", "period": "20131231", "fy": "2013", "fp": "FY", "filed": "20140301", "accepted": "2014-03-01 10:00:00.0", "instance": "one-amend.xml", "prevrpt": "1", "nciks": "1", "aciks": "" , "afs": "LAF"},
        {"adsh": "D", "cik": "200", "name": "Two", "form": "10-K", "period": "20131231", "fy": "2013", "fp": "FY", "filed": "20140202", "accepted": "2014-02-02 10:00:00.0", "instance": "two.xml", "prevrpt": "0", "nciks": "1", "aciks": "", "afs": "AFS"},
        {"adsh": "X", "cik": "300", "name": "Other", "form": "10-K", "period": "20131231", "fy": "2013", "fp": "FY", "filed": "20140203", "accepted": "2014-02-03 10:00:00.0", "instance": "other.xml", "prevrpt": "0", "nciks": "1", "aciks": "", "afs": "LAF"},
        {"adsh": "Q", "cik": "100", "name": "One", "form": "10-Q", "period": "20130930", "fy": "2013", "fp": "Q3", "filed": "20131101", "accepted": "2013-11-01 10:00:00.0", "instance": "one-q.xml", "prevrpt": "0", "nciks": "1", "aciks": "", "afs": "LAF"},
    ]
    pre_fields = ["adsh", "report", "line", "stmt", "inpth", "rfile", "tag", "version", "plabel", "negating"]
    pre_rows = [
        {"adsh": "A", "report": "1", "line": "1", "stmt": "IS", "inpth": "0", "rfile": "H", "tag": "Revenue", "version": "us-gaap/2013", "plabel": "Revenue", "negating": "0"},
        {"adsh": "A", "report": "1", "line": "2", "stmt": "BS", "inpth": "0", "rfile": "H", "tag": "Assets", "version": "us-gaap/2013", "plabel": "Assets", "negating": "0"},
        {"adsh": "A", "report": "2", "line": "1", "stmt": "CP", "inpth": "1", "rfile": "H", "tag": "NoteOnly", "version": "us-gaap/2013", "plabel": "Note", "negating": "0"},
        {"adsh": "B", "report": "1", "line": "1", "stmt": "IS", "inpth": "0", "rfile": "H", "tag": "Revenue", "version": "us-gaap/2013", "plabel": "Amended Revenue", "negating": "0"},
        {"adsh": "D", "report": "1", "line": "1", "stmt": "IS", "inpth": "0", "rfile": "H", "tag": "Income", "version": "us-gaap/2013", "plabel": "Income", "negating": "0"},
        {"adsh": "X", "report": "1", "line": "1", "stmt": "IS", "inpth": "0", "rfile": "H", "tag": "Revenue", "version": "us-gaap/2013", "plabel": "Other issuer", "negating": "0"},
        {"adsh": "Q", "report": "1", "line": "1", "stmt": "IS", "inpth": "0", "rfile": "H", "tag": "Revenue", "version": "us-gaap/2013", "plabel": "Quarter", "negating": "0"},
    ]
    num_fields = ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value", "footnote"]

    def fact(adsh, tag, ddate, qtrs, value, **kwargs):
        return {"adsh": adsh, "tag": tag, "version": "us-gaap/2013", "ddate": ddate, "qtrs": str(qtrs), "uom": "USD", "segments": "", "coreg": "", "value": str(value), "footnote": ""} | kwargs

    amount = changed_value if changed_value is not None else "10"
    num_rows = [
        fact("A", "Revenue", "20131229", 4, amount),  # period and ddate differ by two days
        fact("A", "Revenue", "20131229", 4, "10"),  # duplicate, possibly conflicting
        fact("A", "Assets", "20131231", 0, "100"),
        fact("A", "Revenue", "20131229", 1, "8"),
        fact("A", "Revenue", "20131229", 4, "7", segments="Product=Widget"),
        fact("A", "Revenue", "20131229", 4, "6", coreg="001"),
        fact("A", "Revenue", "20131229", 4, "5", uom="CAD"),
        fact("A", "NoteOnly", "20131229", 4, "999"),
        fact("B", "Revenue", "20121231", 4, "9"),  # amendment comparative date retained
        fact("D", "Income", "20131231", 4, "12"),
        fact("X", "Revenue", "20131231", 4, "999"),
        fact("Q", "Revenue", "20130930", 3, "99"),
    ]
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("sub.txt", tsv_bytes(sub_fields, sub_rows))
        zf.writestr("pre.txt", tsv_bytes(pre_fields, pre_rows))
        zf.writestr("num.txt", tsv_bytes(num_fields, num_rows))
    archive.seek(0)
    return archive


class CandidatePanelSyntheticTests(unittest.TestCase):
    def test_two_sources_filter_join_preservation_and_duplicate_audit(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="test-", dir=TEST_ROOT) as tmp:
            output = Path(tmp)
            writers = panel.PanelWriters(output)
            tracker = panel.DuplicateTracker(output / ".test-index.sqlite3")
            try:
                with zipfile.ZipFile(build_zip()) as first:
                    first_summary = panel.extract_archive(first, "fsds-2014q1.zip", {"100", "200"}, writers, tracker)
                with zipfile.ZipFile(build_zip(changed_value="11")) as second:
                    second_summary = panel.extract_archive(second, "fsds-2014q2.zip", {"100", "200"}, writers, tracker)
            finally:
                writers.close()
                duplicates = tracker.summary()
                tracker.close()

            with (output / "submissions.csv").open(newline="", encoding="utf-8") as stream:
                submissions = list(csv.DictReader(stream))
            with (output / "presentation.csv").open(newline="", encoding="utf-8") as stream:
                presentations = list(csv.DictReader(stream))
            with (output / "statement-facts.csv").open(newline="", encoding="utf-8") as stream:
                facts = list(csv.DictReader(stream))

            self.assertEqual([row["adsh"] for row in submissions], ["A", "B", "D", "A", "B", "D"])
            self.assertEqual(submissions[0]["form"], "10-K")
            self.assertEqual(submissions[1]["form"], "10-K/A")
            self.assertEqual(submissions[0]["instance"], "one.xml")
            self.assertIn("prevrpt", submissions[0])
            self.assertIn("nciks", submissions[0])
            self.assertIn("aciks", submissions[0])
            self.assertEqual(submissions[0]["source_zip"], "fsds-2014q1.zip")
            self.assertEqual(len(presentations), 8)  # IS and BS rows only, filing-version-specific
            self.assertNotIn("NoteOnly", [row["tag"] for row in presentations])
            self.assertEqual(first_summary["selected_accession_count"], 3)
            self.assertEqual(second_summary["selected_accession_count"], 3)
            self.assertEqual(first_summary["counts"]["selected_form_rows_noncandidate_cik"], 1)

            revenue_facts = [row for row in facts if row["tag"] == "Revenue" and row["adsh"] == "A"]
            self.assertEqual(len(revenue_facts), 4)  # duplicate source rows retained in each ZIP
            self.assertEqual([row["value"] for row in revenue_facts], ["10", "10", "11", "10"])
            self.assertTrue(all(row["ddate"] == "20131229" for row in revenue_facts))
            self.assertTrue(all(row["source_zip"] in {"fsds-2014q1.zip", "fsds-2014q2.zip"} for row in revenue_facts))
            self.assertTrue(any(row["ddate"] == "20121231" and row["adsh"] == "B" for row in facts))
            self.assertTrue(any(row["qtrs"] == "0" for row in facts))
            self.assertEqual(len([row for row in facts if row["adsh"] == "X"]), 0)
            self.assertEqual(len([row for row in facts if row["adsh"] == "Q"]), 0)
            self.assertEqual(duplicates["within_source"]["fsds-2014q1.zip"]["duplicate_groups"], 1)
            self.assertEqual(duplicates["within_source"]["fsds-2014q1.zip"]["conflicting_value_groups"], 0)
            self.assertEqual(duplicates["within_source"]["fsds-2014q2.zip"]["conflicting_value_groups"], 1)
            self.assertEqual(duplicates["keys_seen_in_multiple_sources"], 4)
            self.assertGreaterEqual(duplicates["across_all_sources"]["conflicting_value_groups"], 1)


if __name__ == "__main__":
    unittest.main()
