"""Check visible text manifests and playback HTML for the user's brand ban."""
import argparse, re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('paths', nargs='+', type=Path)
args = parser.parse_args()
bad = []
for path in args.paths:
    text = path.read_text()
    # Strip URLs, markup and internal imports; inspect actual user-facing strings.
    if path.suffix == '.html':
        text = re.sub(r'<script\b.*?</script>|<style\b.*?</style>', '', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]*>', ' ', text)
    text = re.sub(r'https?://\S+', '', text)
    if re.search(r'(?i)(?<![a-z])lei(?![a-z])|leisignal|雷信号', text):
        bad.append(str(path))
if bad:
    raise SystemExit('Brand text found: ' + ', '.join(bad))
print('Public-text brand check passed; images/audio still require inspection.')
