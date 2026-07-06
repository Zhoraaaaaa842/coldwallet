use regex::Regex;
use tiny_keccak::{Hasher, Keccak};

/// Keccak-256 used for EIP-55 checksum verification
fn keccak256(data: &[u8]) -> [u8; 32] {
    let mut k = Keccak::v256();
    let mut out = [0u8; 32];
    k.update(data);
    k.finalize(&mut out);
    out
}

/// Validates Ethereum address format and verifies EIP-55 mixed-case checksum
/// if the input contains uppercase letters. Returns lowercase normalized address.
pub fn validate_ethereum_address(address: &str) -> Result<String, String> {
    let address = address.trim();

    if !address.starts_with("0x") {
        return Err("Address must start with 0x".to_string());
    }

    if address.len() != 42 {
        return Err("Address must be 42 characters (0x + 40 hex digits)".to_string());
    }

    let hex_part = &address[2..];
    if !hex_part.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err("Address contains invalid characters".to_string());
    }

    // EIP-55: if the address contains any uppercase letter, verify the checksum.
    // All-lowercase and all-uppercase addresses are accepted without checksum check
    // (common when copy-pasting from block explorers).
    let has_upper = hex_part.chars().any(|c| c.is_ascii_uppercase());
    let has_lower = hex_part.chars().any(|c| c.is_ascii_lowercase());
    if has_upper && has_lower {
        // Mixed case → must be a valid EIP-55 checksum address
        let lower = hex_part.to_lowercase();
        let hash = keccak256(lower.as_bytes());
        let expected: String = lower.chars().enumerate().map(|(i, c)| {
            if c.is_ascii_digit() {
                c
            } else {
                // nibble i of hash: byte i/2, high nibble if i even, low if odd
                let byte = hash[i / 2];
                let nibble = if i % 2 == 0 { byte >> 4 } else { byte & 0x0f };
                if nibble >= 8 { c.to_ascii_uppercase() } else { c }
            }
        }).collect();
        if hex_part != expected {
            return Err(format!(
                "Invalid EIP-55 checksum. Expected: 0x{}", expected
            ));
        }
    }

    Ok(format!("0x{}", hex_part.to_lowercase()))
}

/// Validates transaction amount as a decimal string without float precision loss.
/// Accepts values like "0.001", "1", "1.5".
pub fn validate_transaction_amount(amount: &str) -> Result<String, String> {
    let amount = amount.trim();

    if amount.is_empty() {
        return Err("Amount cannot be empty".to_string());
    }

    // Must be digits with optional single dot
    let dot_count = amount.chars().filter(|&c| c == '.').count();
    if dot_count > 1 {
        return Err("Invalid amount format: multiple decimal points".to_string());
    }
    if !amount.chars().all(|c| c.is_ascii_digit() || c == '.') {
        return Err("Amount must contain only digits and a decimal point".to_string());
    }

    let (int_part, frac_part) = if let Some(pos) = amount.find('.') {
        (&amount[..pos], &amount[pos + 1..])
    } else {
        (amount, "")
    };

    // Parse integer part to check it's non-zero or frac is non-zero
    let int_val: u128 = int_part.parse::<u128>()
        .map_err(|_| "Invalid integer part of amount".to_string())?;

    let frac_nonzero = frac_part.chars().any(|c| c != '0');
    if int_val == 0 && !frac_nonzero {
        return Err("Amount must be greater than zero".to_string());
    }

    // Sanity cap: 1,000,000 ETH
    if int_val > 1_000_000 {
        return Err("Amount exceeds maximum limit (1,000,000 ETH)".to_string());
    }

    Ok(amount.to_string())
}

/// Sanitizes contact name
pub fn sanitize_contact_name(name: &str) -> Result<String, String> {
    let name = name.trim();

    if name.is_empty() {
        return Err("Name cannot be empty".to_string());
    }

    if name.len() > 100 {
        return Err("Name must be 100 characters or less".to_string());
    }

    let sanitized: String = name.chars()
        .filter(|c| !c.is_control())
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<&str>>()
        .join(" ");

    if sanitized.is_empty() {
        return Err("Name contains only invalid characters".to_string());
    }

    Ok(sanitized)
}

/// Validates password strength
pub fn validate_password_strength(password: &str) -> Result<(), String> {
    if password.len() < 12 {
        return Err("Password must be at least 12 characters long".to_string());
    }

    if password.len() > 128 {
        return Err("Password must be 128 characters or less".to_string());
    }

    let has_lowercase = password.chars().any(|c| c.is_lowercase());
    let has_uppercase = password.chars().any(|c| c.is_uppercase());
    let has_digit = password.chars().any(|c| c.is_numeric());
    let has_special = password.chars().any(|c| !c.is_alphanumeric());

    let strength_score = [has_lowercase, has_uppercase, has_digit, has_special]
        .iter()
        .filter(|&&x| x)
        .count();

    if strength_score < 3 {
        return Err("Password must contain at least 3 of: lowercase, uppercase, digits, special characters".to_string());
    }

    let weak_passwords = [
        "password", "123456", "qwerty", "admin", "letmein",
        "welcome", "monkey", "dragon", "master", "sunshine"
    ];
    let password_lower = password.to_lowercase();
    for weak in &weak_passwords {
        if password_lower.contains(weak) {
            return Err("Password contains common weak patterns".to_string());
        }
    }

    Ok(())
}

/// Validates BIP-39 mnemonic phrase.
/// NOTE: duplicate words are intentionally allowed — BIP-39 word list has 2048
/// words and a statistically valid mnemonic can repeat words. The cryptographic
/// checksum (last word encodes entropy checksum bits) is verified by bip39::Mnemonic
/// in commands.rs, not here.
pub fn validate_mnemonic(mnemonic: &str) -> Result<(), String> {
    let words: Vec<&str> = mnemonic.trim().split_whitespace().collect();

    let valid_lengths = [12, 15, 18, 21, 24];
    if !valid_lengths.contains(&words.len()) {
        return Err(format!("Mnemonic must be 12, 15, 18, 21, or 24 words (got {})", words.len()));
    }

    if !mnemonic.is_ascii() {
        return Err("Mnemonic must contain only ASCII characters".to_string());
    }

    // Do NOT check for duplicate words here — BIP-39 mnemonics can legitimately
    // repeat words. The actual checksum is validated by bip39::Mnemonic::parse.
    Ok(())
}

/// Validates gas price (in Gwei)
pub fn validate_gas_price(gas_price: f64) -> Result<(), String> {
    if gas_price <= 0.0 {
        return Err("Gas price must be positive".to_string());
    }

    if gas_price > 10000.0 {
        return Err("Gas price exceeds reasonable limit (10,000 Gwei)".to_string());
    }

    Ok(())
}

/// Validates gas limit
pub fn validate_gas_limit(gas_limit: u64) -> Result<(), String> {
    if gas_limit < 21000 {
        return Err("Gas limit must be at least 21,000".to_string());
    }

    if gas_limit > 10_000_000 {
        return Err("Gas limit exceeds block limit".to_string());
    }

    Ok(())
}

/// Sanitizes file path to prevent directory traversal
pub fn sanitize_file_path(path: &str) -> Result<String, String> {
    if path.contains("..") {
        return Err("Path contains directory traversal".to_string());
    }

    if path.contains('\0') {
        return Err("Path contains null bytes".to_string());
    }

    let sanitized: String = path.chars()
        .filter(|c| !c.is_control() || *c == '\n' || *c == '\r')
        .collect();

    Ok(sanitized)
}

/// Validates network RPC URL
pub fn validate_rpc_url(url: &str) -> Result<(), String> {
    if !url.starts_with("https://") && !url.starts_with("http://localhost") {
        return Err("RPC URL must use HTTPS (or localhost for development)".to_string());
    }

    if url.len() > 500 {
        return Err("RPC URL is too long".to_string());
    }

    let url_regex = Regex::new(r"^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=]+$")
        .map_err(|_| "Invalid regex".to_string())?;

    if !url_regex.is_match(url) {
        return Err("Invalid RPC URL format".to_string());
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_ethereum_address_lowercase() {
        // All-lowercase: no checksum check, always accepted
        assert!(validate_ethereum_address("0x742d35cc6634c0532925a3b844bc9e7595f0beb4").is_ok());
    }

    #[test]
    fn test_validate_ethereum_address_eip55_valid() {
        // Valid EIP-55 checksummed address
        assert!(validate_ethereum_address("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed").is_ok());
    }

    #[test]
    fn test_validate_ethereum_address_eip55_invalid() {
        // Same address with wrong checksum (flip one char case)
        assert!(validate_ethereum_address("0x5aaeb6053F3E94C9b9A09f33669435E7Ef1BeAed").is_err());
    }

    #[test]
    fn test_validate_ethereum_address_invalid() {
        assert!(validate_ethereum_address("0xinvalid").is_err());
        assert!(validate_ethereum_address("742d35cc").is_err());
    }

    #[test]
    fn test_validate_password_strength() {
        assert!(validate_password_strength("StrongP@ssw0rd123").is_ok());
        assert!(validate_password_strength("weak").is_err());
        assert!(validate_password_strength("password123").is_err());
    }

    #[test]
    fn test_validate_transaction_amount() {
        assert!(validate_transaction_amount("1.5").is_ok());
        assert!(validate_transaction_amount("0.000000000000000001").is_ok()); // 1 wei
        assert!(validate_transaction_amount("0").is_err());
        assert!(validate_transaction_amount("0.0").is_err());
        assert!(validate_transaction_amount("-1").is_err());
        assert!(validate_transaction_amount("2000000").is_err());
    }

    #[test]
    fn test_validate_mnemonic_allows_repeated_words() {
        // 12 words with a repeat — must NOT be rejected by this function
        // (BIP-39 checksum validation happens in bip39::Mnemonic::parse)
        let m = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about";
        assert!(validate_mnemonic(m).is_ok());
    }
}
