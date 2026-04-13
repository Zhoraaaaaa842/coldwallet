/**
 * Frontend validation utilities matching backend validation.rs
 */

/**
 * Validate Ethereum address format
 * Checks 0x prefix, 42-char length, hex characters
 */
export function validateEthereumAddress(address: string): { valid: boolean; error?: string } {
  const trimmed = address.trim()
  
  if (!trimmed) {
    return { valid: false, error: 'Адрес обязателен' }
  }
  
  if (!trimmed.startsWith('0x')) {
    return { valid: false, error: 'Адрес должен начинаться с 0x' }
  }
  
  if (trimmed.length !== 42) {
    return { valid: false, error: 'Неверная длина адреса (должно быть 42 символа)' }
  }
  
  if (!/^0x[0-9a-fA-F]{40}$/.test(trimmed)) {
    return { valid: false, error: 'Неверный формат адреса (должен содержать 0-9 и a-f)' }
  }
  
  return { valid: true }
}

/**
 * Validate password strength
 * Min 12 chars, max 128, requires 3/4 char classes
 */
export function validatePasswordStrength(password: string): { valid: boolean; error?: string; score?: number } {
  if (!password) {
    return { valid: false, error: 'Пароль обязателен' }
  }
  
  if (password.length < 12) {
    return { valid: false, error: 'Пароль должен содержать минимум 12 символов' }
  }
  
  if (password.length > 128) {
    return { valid: false, error: 'Пароль не может быть длиннее 128 символов' }
  }
  
  // Check character classes (need at least 3 of 4)
  let charClasses = 0
  if (/[A-ZА-Я]/.test(password)) charClasses++
  if (/[a-zа-я]/.test(password)) charClasses++
  if (/[0-9]/.test(password)) charClasses++
  if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) charClasses++
  
  if (charClasses < 3) {
    return { valid: false, error: 'Пароль должен содержать как минимум 3 из 4 типов символов (заглавные, строчные, цифры, специальные)' }
  }
  
  // Check common weak passwords
  const weakPasswords = ['password', '123456789012', 'qwerty12345678', 'abcdef12345678']
  if (weakPasswords.includes(password.toLowerCase())) {
    return { valid: false, error: 'Этот пароль слишком простой, используйте другой' }
  }
  
  // Calculate score (0-4)
  let score = 0
  if (password.length >= 12) score++
  if (/[A-ZА-Я]/.test(password) && /[a-zа-я]/.test(password)) score++
  if (/[0-9]/.test(password)) score++
  if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) score++
  
  return { valid: true, score }
}

/**
 * Validate mnemonic phrase
 * Checks word count (12/15/18/21/24), ASCII-only, no duplicate words
 */
export function validateMnemonic(mnemonic: string): { valid: boolean; error?: string; wordCount?: number } {
  if (!mnemonic || !mnemonic.trim()) {
    return { valid: false, error: 'Мнемоническая фраза обязательна' }
  }
  
  // Check for non-ASCII characters
  if (/[^\x00-\x7F]/.test(mnemonic)) {
    return { valid: false, error: 'Мнемоническая фраза должна содержать только ASCII символы' }
  }
  
  const words = mnemonic.trim().split(/\s+/)
  const wordCount = words.length
  
  // Check word count (must be 12, 15, 18, 21, or 24)
  if (![12, 15, 18, 21, 24].includes(wordCount)) {
    return { valid: false, error: `Мнемоническая фраза должна содержать 12, 15, 18, 21 или 24 слова (сейчас ${wordCount})` }
  }
  
  // Check for duplicate words (warning only)
  const uniqueWords = new Set(words.map(w => w.toLowerCase()))
  if (uniqueWords.size !== words.length) {
    console.warn('Duplicate words detected in mnemonic phrase')
  }
  
  return { valid: true, wordCount }
}

/**
 * Validate transaction amount
 * Positive, finite, max 1M ETH
 */
export function validateTransactionAmount(amount: string): { valid: boolean; error?: string } {
  if (!amount) {
    return { valid: false, error: 'Сумма обязательна' }
  }
  
  const value = parseFloat(amount)
  
  if (isNaN(value)) {
    return { valid: false, error: 'Неверный формат суммы' }
  }
  
  if (!isFinite(value)) {
    return { valid: false, error: 'Сумма должна быть конечным числом' }
  }
  
  if (value <= 0) {
    return { valid: false, error: 'Сумма должна быть больше 0' }
  }
  
  if (value > 1_000_000) {
    return { valid: false, error: 'Максимальная сумма: 1,000,000 ETH' }
  }
  
  return { valid: true }
}

/**
 * Sanitize contact name
 * Trims, max 100 chars, removes control characters, normalizes whitespace
 */
export function sanitizeContactName(name: string): { valid: boolean; sanitized?: string; error?: string } {
  if (!name || !name.trim()) {
    return { valid: false, error: 'Имя обязательно' }
  }
  
  const trimmed = name.trim()
  
  if (trimmed.length > 100) {
    return { valid: false, error: 'Имя не может быть длиннее 100 символов' }
  }
  
  // Check for control characters
  if (/[\x00-\x1F\x7F]/.test(trimmed)) {
    return { valid: false, error: 'Имя содержит недопустимые символы' }
  }
  
  // Normalize whitespace (replace multiple spaces with single space)
  const sanitized = trimmed.replace(/\s+/g, ' ')
  
  return { valid: true, sanitized }
}

/**
 * Validate gas price
 * Positive, max 10,000 Gwei
 */
export function validateGasPrice(gasPrice: number): { valid: boolean; error?: string } {
  if (!gasPrice || gasPrice <= 0) {
    return { valid: false, error: 'Gas price должна быть больше 0' }
  }
  
  if (gasPrice > 10_000) {
    return { valid: false, error: 'Максимальная gas price: 10,000 Gwei' }
  }
  
  return { valid: true }
}

/**
 * Validate gas limit
 * Min 21,000, max 10M
 */
export function validateGasLimit(gasLimit: number): { valid: boolean; error?: string } {
  if (!gasLimit || gasLimit < 21_000) {
    return { valid: false, error: 'Минимальный gas limit: 21,000' }
  }
  
  if (gasLimit > 10_000_000) {
    return { valid: false, error: 'Максимальный gas limit: 10,000,000' }
  }
  
  return { valid: true }
}

/**
 * Sanitize input data (general purpose)
 * Removes control characters, trims, normalizes whitespace
 */
export function sanitizeInput(input: string): string {
  if (!input) return ''
  
  // Trim and remove control characters
  const sanitized = input.trim().replace(/[\x00-\x1F\x7F]/g, '')
  
  // Normalize whitespace
  return sanitized.replace(/\s+/g, ' ')
}
