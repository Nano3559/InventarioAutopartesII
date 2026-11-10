"""Ejecutor H4 desde cualquier directorio, sin generar registros oficiales."""
import argparse
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--pattern", default="test_*.py")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--list", action="store_true", help="Solo descubrir; no ejecutar pruebas.")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    sys.path.insert(0, str(folder))
    loader = unittest.TestLoader()
    suite = loader.discover(str(folder / "tests"), pattern=args.pattern, top_level_dir=str(folder))
    if args.list:
        def cases(group):
            for case in group:
                if isinstance(case, unittest.TestSuite):
                    yield from cases(case)
                else:
                    yield case.id()
        for name in cases(suite):
            print(name)
        print(f"Pruebas descubiertas: {suite.countTestCases()}")
        return bool(loader.errors)
    return not unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite).wasSuccessful()


if __name__ == "__main__":
    sys.exit(main())
