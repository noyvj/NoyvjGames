"""Dev aid: python3 tools/setstock.py <shift id> '<python dict>' -- rewrite the shelf of one shift in its chapter file and drop
any scan whose supply is not on the shelf."""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lexicon as lx  # noqa: E402


def main(sid, stock_text):
    stock = ast.literal_eval(stock_text)
    path = ROOT / ("cases_%s.py" % sid.split("-")[0])
    text = path.read_text(encoding="utf-8")
    start = text.index('S("%s"' % sid)
    nxt = text.find('    S("', start + 5)
    block = text[start:nxt if nxt != -1 else len(text)]
    new = re.sub(r'(\n\s+"[a-z ]+", )\{[^}]*\}', lambda m: m.group(1) + repr(stock).replace("'", '"'), block, count=1)
    tests = re.search(r'tests="([a-z ]*)"', new)
    if tests:
        keep = [t for t in tests.group(1).split() if stock.get(lx.TEST_BY_ID[t]["item"], 0) > 0]
        new = new.replace(tests.group(0), 'tests="%s"' % " ".join(keep))
    path.write_text(text.replace(block, new), encoding="utf-8")


main(sys.argv[1], sys.argv[2])
