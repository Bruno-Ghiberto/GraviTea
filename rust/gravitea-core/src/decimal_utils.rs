use rust_decimal::Decimal;
use std::str::FromStr;

use super::errors::GraviteaError;

pub fn parse_decimal(s: &str) -> Result<Decimal, GraviteaError> {
    Decimal::from_str(s).map_err(|e| GraviteaError::ComputeError {
        msg: format!("Invalid decimal string '{}': {}", s, e),
    })
}

pub fn decimal_to_string(d: &Decimal) -> String {
    d.normalize().to_string()
}

pub fn dual_tolerance_eq(
    expected: &Decimal,
    actual: &Decimal,
    abs_tol: &Decimal,
    rel_tol: &Decimal,
) -> bool {
    let diff = (*expected - *actual).abs();
    if diff <= *abs_tol {
        return true;
    }
    if *expected != Decimal::ZERO && diff <= *rel_tol * expected.abs() {
        return true;
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_decimal_macros::dec;

    #[test]
    fn test_parse_valid_decimals() {
        assert_eq!(parse_decimal("0").unwrap(), dec!(0));
        assert_eq!(parse_decimal("0.001").unwrap(), dec!(0.001));
        assert_eq!(
            parse_decimal("99999999999999.999").unwrap(),
            Decimal::from_str("99999999999999.999").unwrap()
        );
        assert_eq!(parse_decimal("-1234.567").unwrap(), dec!(-1234.567));
    }

    #[test]
    fn test_parse_invalid_string() {
        let result = parse_decimal("abc");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, GraviteaError::ComputeError { .. }));
        assert!(err.to_string().contains("Invalid decimal string"));
    }

    #[test]
    fn test_roundtrip_normalize() {
        let d1 = Decimal::from_str("10.500").unwrap();
        assert_eq!(decimal_to_string(&d1), "10.5");

        let d2 = Decimal::from_str("0.000").unwrap();
        assert_eq!(decimal_to_string(&d2), "0");

        let d3 = Decimal::from_str("99999999999999.999").unwrap();
        assert_eq!(decimal_to_string(&d3), "99999999999999.999");
    }

    #[test]
    fn test_dual_tolerance_boundary() {
        let abs_tol = dec!(0.01);
        let rel_tol = dec!(0.0001);

        // Absolute: diff=0.01 passes
        assert!(dual_tolerance_eq(&dec!(100), &dec!(100.01), &abs_tol, &rel_tol));

        // Absolute: diff=0.011 fails on small values (relative also fails)
        assert!(!dual_tolerance_eq(
            &dec!(100),
            &dec!(100.011),
            &abs_tol,
            &rel_tol
        ));

        // Relative tolerance kicks in on large values: diff=5 on expected=100000
        // rel_tol * |expected| = 0.0001 * 100000 = 10 → diff=5 <= 10 → passes
        assert!(dual_tolerance_eq(
            &dec!(100000),
            &dec!(100005),
            &abs_tol,
            &rel_tol
        ));

        // Relative fails when diff exceeds both: diff=15 on expected=100000
        // abs: 15 > 0.01 → fail; rel: 15 > 10 → fail
        assert!(!dual_tolerance_eq(
            &dec!(100000),
            &dec!(100015),
            &abs_tol,
            &rel_tol
        ));
    }
}
