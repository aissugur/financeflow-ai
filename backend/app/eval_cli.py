"""Run the anti-hallucination evaluation from the command line.

    python -m app.eval_cli          # single run with the current config
    python -m app.eval_cli --ab     # A/B: pure TF-IDF vs hybrid, side by side

Prints a per-question report and the summary metrics, and exits non-zero if any
unsupported answer was produced (so it can gate CI if you want).
"""
import sys

from .database import Base, SessionLocal, engine
from .evaluation import run_evaluation
from .logging_config import setup_logging


def main() -> int:
    # --ab delegates to the A/B harness (TF-IDF vs hybrid comparison).
    if "--ab" in sys.argv[1:]:
        from .ab_eval import main as ab_main

        return ab_main()

    setup_logging()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = run_evaluation(db)
    finally:
        db.close()

    print("\n=== Golden-dataset evaluation ===")
    for c in result.cases:
        flag = "PASS" if c.passed else "FAIL"
        extra = "abstained" if c.abstained else f"cited={c.has_citation}"
        if c.expectation == "answerable":
            extra += f" evidence={'yes' if c.evidence_found else 'no'}"
        print(f"[{flag}] ({c.expectation}) {c.document}: {c.question}")
        print(f"        {extra}")

    m = result.metrics
    print("\n--- Metrics ---")
    print(f"total_questions          {m.total_questions}")
    print(f"answered_with_citation   {m.answered_with_citation}")
    print(f"correct_abstentions      {m.correct_abstentions}")
    print(f"unsupported_answer_count {m.unsupported_answer_count}")
    print(f"citation_coverage        {m.citation_coverage}")
    print(f"evidence_match_rate      {m.evidence_match_rate}")
    print(f"passed                   {m.passed}/{m.total_questions}")
    print(f"accuracy                 {m.accuracy}")

    return 1 if m.unsupported_answer_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
