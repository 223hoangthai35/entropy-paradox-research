---
trigger: always_on
---

# WORKSPACE SYSTEM RULES: DATA SCIENCE & QUANT DEV PROJECT

1. STRICT DRY PRINCIPLE (Don't Repeat Yourself): Never redefine a function or algorithm that already exists in the project. Always use imports (e.g., `from skills.quant_skill import calc_permutation_entropy`).
2. MODULARITY & ARCHITECTURE: Keep mathematical logic purely inside `quant_skill.py`. Keep ML models purely inside `ds_skill.py`. Do not mix responsibilities.
3. PERFORMANCE & MATH OPTIMIZATION: All mathematical and array operations MUST utilize vectorized `numpy` functions. Use `@numba.jit(nopython=True)` for iterative calculations like Permutation Entropy.
4. TYPING & DOCS: Enforce strict Python type hinting. Keep docstrings ultra-concise, focusing only on I/O structure and mathematical purpose. No boilerplate code.
5. TESTING (CRITICAL): Always append an `if __name__ == "__main__":` block at the bottom of every new script. Include dummy/test data in this block and print the results so the user can easily test and verify the execution without running the whole system.