# Research: Rust Observability Hot Path (SPEC-021)

**Date**: 2026-02-27
**Branch**: `021-rust-observability-hotpath`
**Spec**: [spec.md](spec.md)

## R-001: Capture Group Classification (RESOLVED in SPECIFY phase)

**Decision**: No patterns use capture groups. All 24 operations are simple `re.sub(pattern, replacement, string)` with literal replacement strings — no `\1`-style backreferences.

**Rationale**: Line-by-line inspection of `metrics.py` lines 40-131 confirmed every pattern uses literal replacement strings (`"/{id}"`, `"/auth-action/"`, `"/{redacted}/"`, etc.). No capture groups exist.

**Impact**: `RegexSet` was initially considered but is not viable — it only supports match/is_match, not substitution. The correct approach is `LazyLock<Regex>` per pattern with `Regex::replace_all()`.

## R-002: LazyLock<Regex> Compilation Cost (RESOLVED)

**Decision**: Use `std::sync::LazyLock<Regex>` for all 24 static patterns. First-call compilation cost is microseconds; subsequent calls are nanosecond-level pointer dereferences.

**Rationale**: The regex crate documentation states compilation takes "a few microseconds to a few milliseconds depending on pattern size." For our simple patterns (word boundaries, character classes, short alternations), expect single-digit microsecond compilation. After first initialization, `LazyLock` performs a single atomic `Acquire` load per access — effectively zero cost. No recompilation, no cache lookup, no allocation.

**Alternatives considered**:
- `once_cell::sync::Lazy`: Functionally equivalent but `LazyLock` is now in stdlib (stable since Rust 1.80). No need for external crate.
- `lazy_static!`: Legacy macro-based approach. `LazyLock` is the recommended replacement.
- Compile at function call: Rejected — would recompile 24 patterns on every HTTP request.

## R-003: Pattern Ordering Verification (RESOLVED)

**Decision**: Sequential `Regex::replace_all()` in a loop produces identical results to Python's `re.sub()` in a loop, given the same pattern order.

**Rationale**: Each `replace_all()` call operates on the full string left-to-right and produces a new string. The order of application is determined entirely by the loop iteration order, not the regex engine. Our patterns are stored in ordered arrays (`PATH_NORMALIZERS`, `SENSITIVE_ENDPOINT_PATTERNS`, plus 6 inline calls), and the Rust implementation must iterate them in the same order.

**Edge case — empty match divergence**: Rust's `replace_all` excludes empty matches that overlap with preceding non-empty matches, while Python 3.7+ reports them. This only affects patterns using `*`, `?`, or `{0,n}` quantifiers. **None of our 24 patterns can produce zero-length matches** (they all require at least one character: `/`, `\d+`, `[^/]+`, `\b\w+\b`). No risk.

## R-004: Rust `\b` Word Boundary Compatibility (RESOLVED)

**Decision**: For ASCII input, Rust's `\b` behaves identically to Python's `\b`. No code changes needed.

**Rationale**: Both engines define word characters (`\w`) identically for ASCII: `[a-zA-Z0-9_]`. Word boundaries (`\b`) match at positions between a word character and a non-word character. Since our URL paths are standard ASCII HTTP paths, the behavior is identical.

**Unicode caveat**: For Unicode text, Rust and Python define `\w` slightly differently (Rust includes Mark characters and Join Control; Python includes `Other_Number`). Our spec explicitly states "only ASCII keyword matching applies; non-ASCII content passes through unchanged" (Assumption in spec.md). Since our sensitive keywords are all ASCII (`password`, `token`, `secret`, `credential`, `api-key`, `private-key`), no divergence is possible.

**Alternatives considered**:
- `(?-u:\b)` to force ASCII-only word boundaries: Not needed since our patterns only match ASCII keywords and our input is standard HTTP paths.

## R-005: `re.IGNORECASE` vs `(?i)` Equivalence (RESOLVED)

**Decision**: For ASCII input, Rust's `(?i)` is identical to Python's `re.IGNORECASE`. Use `(?i)` prefix in all 22 sanitization patterns.

**Rationale**: Both engines fold `a-z` to `A-Z` and vice versa for ASCII characters. Both use Unicode "Simple Case Folding" by default for non-ASCII (one codepoint maps to exactly one codepoint). Neither supports "full" case folding (e.g., German eszett `ß` to `SS`).

Since all 22 sanitization patterns match only ASCII keywords (`password`, `token`, `secret`, etc.), the case folding behavior is identical between Rust and Python. No edge cases exist for our use case.

## Summary

| ID | Topic | Status | Decision |
|----|-------|--------|----------|
| R-001 | Capture group classification | RESOLVED | No capture groups — use `LazyLock<Regex>` per pattern |
| R-002 | LazyLock compilation cost | RESOLVED | Microseconds first call, nanoseconds after — acceptable |
| R-003 | Pattern ordering | RESOLVED | Identical to Python loop order; no empty-match risk |
| R-004 | `\b` compatibility | RESOLVED | Identical for ASCII; Unicode differences irrelevant for our patterns |
| R-005 | `(?i)` equivalence | RESOLVED | Identical for ASCII; both use simple case folding |

All research topics resolved. No NEEDS CLARIFICATION items remain. Ready for implementation planning.
