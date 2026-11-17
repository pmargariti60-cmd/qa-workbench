# QA manifesto

1. Run the same assertion in each environment before attributing differences to the build.
2. Capture the environment, revision when known, observed behavior, and browser evidence.
3. Distinguish a product failure from an environment or runner failure.
4. Keep smoke checks short and deterministic. Use targeted exploration to investigate what failed.
5. Verify AI-generated reports against the run. A tester owns severity and release decisions.
