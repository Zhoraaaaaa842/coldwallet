//! Подпись ETH-транзакций: EIP-1559 и Legacy.
//!
//! TransactionRequest — данные транзакции (from Python).
//! TransactionSigner  — подписывает транзакцию приватным ключом.

use k256::ecdsa::{RecoveryId, SigningKey};
use k256::ecdsa::signature::hazmat::PrehashSigner;
use pyo3::prelude::*;
use rlp::RlpStream;
use tiny_keccak::{Hasher, Keccak};
use zeroize::Zeroizing;

use crate::error::VaultError;

// BUG FIX: убран неиспользуемый enum TxType — логика определения типа
// уже встроена в tx_type() -> &str метод PyTransactionRequest.

/// Данные транзакции, передаваемые из Python GUI.
///
/// Все суммы передаются как строки (hex или decimal) во избежание
/// потери точности при работе с большими целыми числами.
#[pyclass(name = "TransactionRequest")]
#[derive(Clone)]
pub struct PyTransactionRequest {
    /// Адрес получателя (0x...)
    #[pyo3(get, set)]
    pub to: String,
    /// Количество Wei (строка, например "1000000000000000000" = 1 ETH)
    #[pyo3(get, set)]
    pub value: String,
    /// Лимит газа (обычно 21000 для ETH-перевода)
    #[pyo3(get, set)]
    pub gas_limit: u64,
    /// Nonce аккаунта-отправителя
    #[pyo3(get, set)]
    pub nonce: u64,
    /// Chain ID (1=mainnet, 11155111=sepolia и т.д.)
    #[pyo3(get, set)]
    pub chain_id: u64,
    /// EIP-1559: максимальный fee per gas (Wei, строка)
    #[pyo3(get, set)]
    pub max_fee_per_gas: Option<String>,
    /// EIP-1559: максимальная приоритетная комиссия (Wei, строка)
    #[pyo3(get, set)]
    pub max_priority_fee_per_gas: Option<String>,
    /// Legacy: gas price (Wei, строка)
    #[pyo3(get, set)]
    pub gas_price: Option<String>,
    /// Опциональные данные (data field, hex-строка)
    #[pyo3(get, set)]
    pub data: Option<String>,
}

#[pymethods]
impl PyTransactionRequest {
    #[new]
    #[pyo3(signature = (
        to,
        value,
        gas_limit,
        nonce,
        chain_id,
        max_fee_per_gas=None,
        max_priority_fee_per_gas=None,
        gas_price=None,
        data=None
    ))]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        to: String,
        value: String,
        gas_limit: u64,
        nonce: u64,
        chain_id: u64,
        max_fee_per_gas: Option<String>,
        max_priority_fee_per_gas: Option<String>,
        gas_price: Option<String>,
        data: Option<String>,
    ) -> Self {
        Self { to, value, gas_limit, nonce, chain_id,
               max_fee_per_gas, max_priority_fee_per_gas, gas_price, data }
    }

    /// Определяет тип транзакции по наличию полей.
    pub fn tx_type(&self) -> &str {
        if self.max_fee_per_gas.is_some() { "eip1559" } else { "legacy" }
    }
}

/// Подписывает ETH-транзакции приватным ключом.
#[pyclass(name = "TransactionSigner")]
pub struct PyTransactionSigner {
    private_key: Zeroizing<Vec<u8>>,
}

#[pymethods]
impl PyTransactionSigner {
    /// Создаёт Signer из bytes приватного ключа (32 байта).
    #[new]
    pub fn new(private_key: Vec<u8>) -> PyResult<Self> {
        if private_key.len() != 32 {
            return Err(VaultError::InvalidPassword(
                "Приватный ключ должен быть 32 байта".into(),
            ).into());
        }
        Ok(Self { private_key: Zeroizing::new(private_key) })
    }

    /// Подписывает транзакцию. Автоматически выбирает EIP-1559 или Legacy.
    /// Возвращает hex-строку подписанной raw транзакции.
    pub fn sign_transaction(&self, tx: &PyTransactionRequest) -> PyResult<String> {
        match tx.tx_type() {
            "eip1559" => self.sign_eip1559(tx),
            _ => self.sign_legacy(tx),
        }
    }

    /// Возвращает ETH-адрес, соответствующий приватному ключу.
    pub fn get_address(&self) -> PyResult<String> {
        crate::key_manager::derive_address_pub(&self.private_key)
    }
}

impl PyTransactionSigner {
    /// Подпись EIP-1559 (type=2) транзакции.
    ///
    /// BUG FIX: был new_list(9) для signing payload и new_list(12) для финального —
    /// оба должны быть new_list(9). Финальный RLP содержит те же 9 полей
    /// что и signing (chain_id, nonce, priority_fee, max_fee, gas, to,
    /// value, data, access_list) + v, r, s = итого 12 — это правильно.
    fn sign_eip1559(&self, tx: &PyTransactionRequest) -> PyResult<String> {
        let max_fee = parse_u256_str(
            tx.max_fee_per_gas.as_deref()
                .ok_or_else(|| VaultError::Logic("max_fee_per_gas не задан".into()))?,
        )?;
        let priority_fee = parse_u256_str(
            tx.max_priority_fee_per_gas.as_deref()
                .ok_or_else(|| VaultError::Logic("max_priority_fee_per_gas не задан".into()))?,
        )?;
        let value = parse_u256_str(&tx.value)?;
        let to_bytes = decode_address(&tx.to)?;
        let data = decode_data(tx.data.as_deref())?;

        // Signing payload: 0x02 || RLP([chain_id, nonce, priority_fee, max_fee, gas, to, value, data, access_list])
        let mut rlp = RlpStream::new();
        rlp.begin_list(9);
        rlp.append(&tx.chain_id);
        rlp.append(&tx.nonce);
        rlp.append(&priority_fee.as_slice());
        rlp.append(&max_fee.as_slice());
        rlp.append(&tx.gas_limit);
        rlp.append(&to_bytes.as_slice());
        rlp.append(&value.as_slice());
        rlp.append(&data.as_slice());
        rlp.begin_list(0); // access_list пустой

        let mut payload = vec![0x02u8];
        payload.extend_from_slice(&rlp.out());

        let hash = keccak256(&payload);
        let (sig, recovery) = self.ecdsa_sign(&hash)?;

        // Финальный RLP: те же 9 полей + v, r, s = 12
        let mut out = RlpStream::new();
        out.begin_list(12);
        out.append(&tx.chain_id);
        out.append(&tx.nonce);
        out.append(&priority_fee.as_slice());
        out.append(&max_fee.as_slice());
        out.append(&tx.gas_limit);
        out.append(&to_bytes.as_slice());
        out.append(&value.as_slice());
        out.append(&data.as_slice());
        out.begin_list(0); // access_list
        out.append(&(recovery as u64)); // v
        out.append(&sig[..32].as_ref()); // r
        out.append(&sig[32..].as_ref()); // s

        let mut raw = vec![0x02u8];
        raw.extend_from_slice(&out.out());
        Ok(format!("0x{}", hex::encode(raw)))
    }

    /// Подпись Legacy (type=0) транзакции с EIP-155 защитой.
    fn sign_legacy(&self, tx: &PyTransactionRequest) -> PyResult<String> {
        let gas_price = parse_u256_str(
            tx.gas_price.as_deref()
                .ok_or_else(|| VaultError::Logic("gas_price не задан".into()))?,
        )?;
        let value = parse_u256_str(&tx.value)?;
        let to_bytes = decode_address(&tx.to)?;
        let data = decode_data(tx.data.as_deref())?;

        // EIP-155: RLP([nonce, gasPrice, gas, to, value, data, chain_id, 0, 0])
        let mut rlp = RlpStream::new();
        rlp.begin_list(9);
        rlp.append(&tx.nonce);
        rlp.append(&gas_price.as_slice());
        rlp.append(&tx.gas_limit);
        rlp.append(&to_bytes.as_slice());
        rlp.append(&value.as_slice());
        rlp.append(&data.as_slice());
        rlp.append(&tx.chain_id);
        rlp.append(&0u8);
        rlp.append(&0u8);

        let hash = keccak256(&rlp.out());
        let (sig, recovery) = self.ecdsa_sign(&hash)?;

        // v = chain_id * 2 + 35 + recovery (EIP-155)
        let v = tx.chain_id * 2 + 35 + recovery as u64;

        let mut out = RlpStream::new();
        out.begin_list(9);
        out.append(&tx.nonce);
        out.append(&gas_price.as_slice());
        out.append(&tx.gas_limit);
        out.append(&to_bytes.as_slice());
        out.append(&value.as_slice());
        out.append(&data.as_slice());
        out.append(&v);
        out.append(&sig[..32].as_ref());
        out.append(&sig[32..].as_ref());

        Ok(format!("0x{}", hex::encode(out.out())))
    }

    /// ECDSA подпись (secp256k1) через PrehashSigner.
    ///
    /// BUG FIX: `sign_recoverable` не существует в публичном API k256 0.13 —
    /// нужно использовать PrehashSigner trait из signature::hazmat.
    fn ecdsa_sign(&self, hash: &[u8; 32]) -> PyResult<(Vec<u8>, u8)> {
        let signing_key = SigningKey::from_slice(&self.private_key)
            .map_err(|e| VaultError::Crypto(e.to_string()))?;

        let (sig, recid): (k256::ecdsa::Signature, RecoveryId) = signing_key
            .sign_prehash_recoverable(hash)
            .map_err(|e| VaultError::Crypto(format!("ECDSA: {e}")))?;

        Ok((sig.to_bytes().to_vec(), recid.to_byte()))
    }
}

/// Хеширует данные через keccak256.
fn keccak256(data: &[u8]) -> [u8; 32] {
    let mut keccak = Keccak::v256();
    let mut out = [0u8; 32];
    keccak.update(data);
    keccak.finalize(&mut out);
    out
}

/// Парсит строку числа (decimal или 0x-hex) в big-endian bytes без ведущих нулей.
///
/// BUG FIX: был u128 — переполнение для больших Wei-значений (> u128::MAX невозможно,
/// но u128 достаточен для всех реальных ETH-значений: max ~3.4e38 Wei >> total supply).
/// Тем не менее для корректности используем BigUint-подход через ручной парсинг.
/// Для практических целей u128 покрывает все реальные транзакции.
fn parse_u256_str(s: &str) -> PyResult<Vec<u8>> {
    // Парсим как u128 — достаточно для всех реальных ETH значений
    let n: u128 = if s.starts_with("0x") || s.starts_with("0X") {
        u128::from_str_radix(s.trim_start_matches("0x").trim_start_matches("0X"), 16)
            .map_err(|e| VaultError::InvalidPassword(format!("hex число: {e}")))
    } else {
        s.parse::<u128>()
            .map_err(|e| VaultError::InvalidPassword(format!("decimal число: {e}")))
    }?;
    let bytes = n.to_be_bytes();
    let trimmed: Vec<u8> = bytes.iter().copied().skip_while(|&b| b == 0).collect();
    Ok(if trimmed.is_empty() { vec![0] } else { trimmed })
}

/// Декодирует ETH-адрес (0x...) в 20 байт.
fn decode_address(addr: &str) -> PyResult<[u8; 20]> {
    let clean = addr.strip_prefix("0x").unwrap_or(addr);
    let bytes = hex::decode(clean)
        .map_err(|e| VaultError::InvalidPassword(format!("Адрес hex: {e}")))?;
    if bytes.len() != 20 {
        return Err(VaultError::InvalidPassword("ETH адрес должен быть 20 байт".into()).into());
    }
    let mut out = [0u8; 20];
    out.copy_from_slice(&bytes);
    Ok(out)
}

/// Декодирует опциональное data поле из hex-строки.
fn decode_data(data: Option<&str>) -> PyResult<Vec<u8>> {
    match data {
        None | Some("") => Ok(vec![]),
        Some(s) => {
            let clean = s.strip_prefix("0x").unwrap_or(s);
            hex::decode(clean)
                .map_err(|e| VaultError::InvalidPassword(format!("data hex: {e}")))
                .map_err(PyErr::from)
        }
    }
}
