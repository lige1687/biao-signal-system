import csv
import io
import unittest
import zipfile
from pathlib import Path
import importlib.util


MODULE_PATH = Path(__file__).with_name("extract_fsds.py")
spec = importlib.util.spec_from_file_location("extract_fsds", MODULE_PATH)
extract_fsds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_fsds)


def make_tsv(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


class KeepOpenStringIO(io.StringIO):
    def close(self):
        pass


class FsdsExtractionSyntheticTests(unittest.TestCase):
    def test_synthetic_zip_preserves_versions_dates_duplicates_and_filters(self):
        sub_fields = ["adsh", "cik", "name", "sic", "period", "fy", "fp", "filed", "accepted", "form"]
        sub_rows = [
            dict(adsh="A", cik="1", name="Issuer", sic="1234", period="20131231", fy="2013", fp="FY", filed="20140201", accepted="2014-02-01 10:00:00.0", form="10-K"),
            dict(adsh="B", cik="1", name="Issuer", sic="1234", period="20131231", fy="2013", fp="FY", filed="20140301", accepted="2014-03-01 11:00:00.0", form="10-K/A"),
            dict(adsh="C", cik="1", name="Issuer", sic="1234", period="20131231", fy="2013", fp="FY", filed="20140202", accepted="2014-02-02 10:00:00.0", form="10-Q"),
        ]
        pre_fields = ["adsh", "report", "line", "stmt", "inpth", "rfile", "tag", "version", "plabel", "negating"]
        pre_rows = [
            dict(adsh="A", report="1", line="1", stmt="IS", inpth="0", rfile="H", tag="Revenue", version="us-gaap/2013", plabel="Revenue", negating="0"),
            dict(adsh="A", report="1", line="2", stmt="IS", inpth="0", rfile="H", tag="Revenue", version="us-gaap/2013", plabel="Revenue duplicate presentation", negating="0"),
            dict(adsh="A", report="2", line="1", stmt="BS", inpth="0", rfile="H", tag="Assets", version="us-gaap/2013", plabel="Assets", negating="0"),
            dict(adsh="B", report="1", line="1", stmt="IS", inpth="0", rfile="H", tag="Revenue", version="us-gaap/2013", plabel="Revenue amendment", negating="0"),
            dict(adsh="C", report="1", line="1", stmt="IS", inpth="0", rfile="H", tag="Revenue", version="us-gaap/2013", plabel="Quarter excluded", negating="0"),
        ]
        num_fields = ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value", "footnote"]
        def fact(adsh, tag, ddate, qtrs, uom, value, version="us-gaap/2013", segments="", coreg="", footnote=""):
            return dict(adsh=adsh, tag=tag, version=version, ddate=ddate, qtrs=qtrs, uom=uom, segments=segments, coreg=coreg, value=value, footnote=footnote)
        num_rows = [
            fact("A", "Revenue", "20131231", "4", "USD", "10", footnote="first duplicate"),
            fact("A", "Revenue", "20131231", "4", "USD", "10", footnote="identical duplicate"),
            fact("A", "Revenue", "20131231", "4", "USD", "11", footnote="conflicting duplicate"),
            fact("A", "Assets", "20131231", "0", "USD", "100"),
            fact("A", "Revenue", "20120930", "1", "USD", "8"),
            fact("A", "Revenue", "20131231", "4", "USD", "7", segments="Business=Retail"),
            fact("A", "Revenue", "20131231", "4", "USD", "6", coreg="0001"),
            fact("A", "Revenue", "20131231", "4", "CAD", "5"),
            fact("A", "Revenue", "20131231", "4", "USD", "4", version="us-gaap/2012"),
            # Amendment accession and old comparative period stay separate; no backfill.
            fact("B", "Revenue", "20120930", "4", "USD", "9"),
            fact("C", "Revenue", "20131231", "4", "USD", "99"),
        ]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sub.txt", make_tsv(sub_fields, sub_rows))
            zf.writestr("pre.txt", make_tsv(pre_fields, pre_rows))
            zf.writestr("num.txt", make_tsv(num_fields, num_rows))
        archive.seek(0)
        outputs = {name: KeepOpenStringIO(newline="") for name in extract_fsds.OUTPUTS[:3]}
        with zipfile.ZipFile(archive) as zf:
            result = extract_fsds.extract_archive(zf, lambda name: outputs[name], extract_fsds.MemoryDuplicateTracker())

        submissions = list(csv.DictReader(io.StringIO(outputs["annual-submissions.csv"].getvalue())))
        presentations = list(csv.DictReader(io.StringIO(outputs["presentation.csv"].getvalue())))
        facts = list(csv.DictReader(io.StringIO(outputs["statement-facts.csv"].getvalue())))
        self.assertEqual([row["adsh"] for row in submissions], ["A", "B"])
        self.assertEqual(list(submissions[0]), extract_fsds.SUBMISSION_FIELDS)
        self.assertEqual(len(presentations), 4)  # preserves repeated PRE presentation rows
        self.assertEqual(len(facts), 5)  # duplicate numeric facts remain separate rows
        self.assertEqual([row["value"] for row in facts[:3]], ["10", "10", "11"])
        self.assertEqual(facts[0]["footnote"], "first duplicate")
        self.assertEqual(facts[-1]["adsh"], "B")
        self.assertEqual(facts[-1]["ddate"], "20120930")  # comparative period is preserved
        self.assertEqual(result["selected_form_counts"], {"10-K": 1, "10-K/A": 1})
        self.assertEqual(result["duplicate_audit"], {"duplicate_groups": 1, "duplicate_extra_rows": 2, "conflicting_value_groups": 1})
        self.assertEqual(result["counts"]["excluded_non_usd"], 1)
        self.assertEqual(result["counts"]["excluded_qtrs_not_0_or_4"], 1)
        self.assertEqual(result["counts"]["excluded_nonempty_segments"], 1)
        self.assertEqual(result["counts"]["excluded_nonempty_coreg"], 1)
        self.assertEqual(result["counts"]["excluded_union"], 4)
        self.assertEqual(result["counts"]["num_rows_without_selected_is_bs_presentation_match"], 2)


if __name__ == "__main__":
    unittest.main()
