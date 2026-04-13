use regex::Regex;

/// Validates Ethereum address format and checksum
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

    // Return lowercase normalized address
    Ok(address.to_lowercase())
}

/// Validates transaction amount
pub fn validate_transaction_amount(amount: &str) -> Result<f64, String> {
    let value = amount.trim().parse::<f64>()
        .map_err(|_| "Invalid amount format".to_string())?;

    if value <= 0.0 {
        return Err("Amount must be positive".to_string());
    }

    if !value.is_finite() {
        return Err("Amount must be a finite number".to_string());
    }

    if value > 1_000_000.0 {
        return Err("Amount exceeds maximum limit (1,000,000 ETH)".to_string());
    }

    Ok(value)
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

    // Remove control characters and normalize whitespace
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

    // Check for common weak passwords
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

/// Validates mnemonic phrase
pub fn validate_mnemonic(mnemonic: &str) -> Result<(), String> {
    let words: Vec<&str> = mnemonic.trim().split_whitespace().collect();

    let valid_lengths = [12, 15, 18, 21, 24];
    if !valid_lengths.contains(&words.len()) {
        return Err(format!("Mnemonic must be 12, 15, 18, 21, or 24 words (got {})", words.len()));
    }

    // Check for non-ASCII characters
    if !mnemonic.is_ascii() {
        return Err("Mnemonic must contain only ASCII characters".to_string());
    }

    // Check for duplicate words (potential typo or manipulation)
    let mut unique_words = words.clone();
    unique_words.sort();
    unique_words.dedup();
    if unique_words.len() != words.len() {
        return Err("Mnemonic contains duplicate words".to_string());
    }

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

    // Remove any control characters
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

    // Basic URL validation
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
    fn test_validate_ethereum_address() {
        assert!(validate_ethereum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb").is_ok());
        assert!(validate_ethereum_address("0xinvalid").is_err());
        assert!(validate_ethereum_address("742d35Cc6634C0532925a3b844Bc9e7595f0bEb").is_err());
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
        assert!(validate_transaction_amount("0").is_err());
        assert!(validate_transaction_amount("-1").is_err());
        assert!(validate_transaction_amount("2000000").is_err());
    }
}
