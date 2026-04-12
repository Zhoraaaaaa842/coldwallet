//! transaction.rs — подпись ETH транзакций (офлайн).
//!
//! Поддерживает:
//!   - EIP-1559 (type 2): maxFeePerGas + maxPriorityFeePerGas
//!   - Legacy (type 0): gasPrice
//!
//! Отличия от Python-версии:
//!   1. Нет зависимостей eth_account/web3 — всё на k256 + rlp.
//!   2. TransactionRequest — обычный Python dataclass-аналог через #[pyclass].
//!   3. Подпись через k256::ecdsa без Python-прослоек.
//!   4. Валидация hex поля data встроена в Rust-тип.

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use k256::{
    ecdsa::{SigningKey, signature::hazmat::PrehashSigner, RecoveryId},
};
use tiny_keccak::{Hasher, Keccak};
use rlp::RlpStream;
use serde_json;

// ─────────────────────────────────────────────────────────────────────────────
// TransactionRequest — параметры транзакции
// ─────────────────────────────────────────────────────────────────────────────

/// Параметры ETH транзакции для подписи.
/// Аналог Python dataclass TransactionRequest.
#[pyclass(module = "coldvault_core")]
#[derive(Clone)]
pub struct TransactionRequest {
    #[pyo3(get, set)] pub to: String,
    #[pyo3(get, set)] pub value_wei: u128,
    #[pyo3(get, set)] pub nonce: u64,
    #[pyo3(get, set)] pub chain_id: u64,
    #[pyo3(get, set)] pub gas_limit: u64,
    // EIP-1559 поля
    #[pyo3(get, set)] pub max_fee_per_gas: Option<u128>,
    #[pyo3(get, set)] pub max_priority_fee_per_gas: Option<u128>,
    // Legacy поле
    #[pyo3(get, set)] pub gas_price: Option<u128>,
    // Поле data (контракты)
    #[pyo3(get, set)] pub data: Option<String>,
}

#[pymethods]
impl TransactionRequest {
    /// Создаёт TransactionRequest.
    #[new]
    #[pyo3(signature = (
        to,
        value_wei,
        nonce,
        chain_id = 1,
        gas_limit = 21000,
        max_fee_per_gas = None,
        max_priority_fee_per_gas = None,
        gas_price = None,
        data = None,
    ))]
    pub fn new(
        to: String,
        value_wei: u128,
        nonce: u64,
        chain_id: u64,
        gas_limit: u64,
        max_fee_per_gas: Option<u128>,
        max_priority_fee_per_gas: Option<u128>,
        gas_price: Option<u128>,
        data: Option<String>,
    ) -> Self {
        TransactionRequest {
            to, value_wei, nonce, chain_id, gas_limit,
            max_fee_per_gas, max_priority_fee_per_gas,
            gas_price, data,
        }
    }

    /// Валидирует параметры транзакции.
    pub fn validate(&self) -> PyResult<()> {
        validate_eth_address(&self.to)?;

        if self.gas_limit < 21000 {
            return Err(PyValueError::new_err("Gas limit не может быть меньше 21000"));
        }

        let has_eip1559 = self.max_fee_per_gas.is_some() && self.max_priority_fee_per_gas.is_some();
        let has_legacy = self.gas_price.is_some();

        if !has_eip1559 && !has_legacy {
            return Err(PyValueError::new_err(
                "Укажите max_fee_per_gas + max_priority_fee_per_gas (EIP-1559) или gas_price (Legacy)"
            ));
        }
        if has_eip1559 && has_legacy {
            return Err(PyValueError::new_err(
                "Нельзя использовать одновременно EIP-1559 и Legacy параметры газа"
            ));
        }
        if has_eip1559 {
            let max_fee = self.max_fee_per_gas.unwrap();
            let priority = self.max_priority_fee_per_gas.unwrap();
            if priority > max_fee {
                return Err(PyValueError::new_err(
                    "max_priority_fee_per_gas не может превышать max_fee_per_gas"
                ));
            }
        }

        // Валидация поля data — только hex
        if let Some(ref d) = self.data {
            let hex_part = d.trim_start_matches("0x").trim_start_matches("0X");
            if !hex_part.is_empty() && !hex_part.chars().all(|c| c.is_ascii_hexdigit()) {
                return Err(PyValueError::new_err(
                    "Поле data должно быть hex-строкой (0x...)"
                ));
            }
        }

        Ok(())
    }

    /// Сериализует неподписанную транзакцию в JSON для USB-передачи.
    pub fn serialize_unsigned(&self) -> PyResult<String> {
        self.validate()?;

        let mut tx = serde_json::json!({
            "type": "unsigned_transaction",
            "version": 1,
            "tx": {
                "to": self.to,
                "value_wei": self.value_wei.to_string(),
                "nonce": self.nonce,
                "chain_id": self.chain_id,
                "gas_limit": self.gas_limit,
            }
        });

        let tx_obj = tx["tx"].as_object_mut().unwrap();

        if let (Some(max_fee), Some(priority)) = (self.max_fee_per_gas, self.max_priority_fee_per_gas) {
            tx_obj.insert("max_fee_per_gas".into(), serde_json::Value::String(max_fee.to_string()));
            tx_obj.insert("max_priority_fee_per_gas".into(), serde_json::Value::String(priority.to_string()));
            tx_obj.insert("tx_type".into(), serde_json::Value::String("eip1559".into()));
        } else if let Some(gp) = self.gas_price {
            tx_obj.insert("gas_price".into(), serde_json::Value::String(gp.to_string()));
            tx_obj.insert("tx_type".into(), serde_json::Value::String("legacy".into()));
        }

        if let Some(ref d) = self.data {
            tx_obj.insert("data".into(), serde_json::Value::String(d.clone()));
        }

        serde_json::to_string_pretty(&tx)
            .map_err(|e| PyRuntimeError::new_err(format!("JSON: {e}")))
    }

    /// Десериализует JSON → TransactionRequest.
    #[staticmethod]
    pub fn deserialize(json_str: String) -> PyResult<TransactionRequest> {
        let data: serde_json::Value = serde_json::from_str(&json_str)
            .map_err(|e| PyValueError::new_err(format!("JSON: {e}")))?;

        if data.get("type").and_then(|v| v.as_str()) != Some("unsigned_transaction") {
            return Err(PyValueError::new_err("Ожидается unsigned_transaction"));
        }

        let tx = &data["tx"];
        let value_wei: u128 = tx["value_wei"].as_str().unwrap_or("0")
            .parse().map_err(|_| PyValueError::new_err("Невалидный value_wei"))?;

        let mut req = TransactionRequest::new(
            tx["to"].as_str().unwrap_or("").to_string(),
            value_wei,
            tx["nonce"].as_u64().unwrap_or(0),
            tx.get("chain_id").and_then(|v| v.as_u64()).unwrap_or(1),
            tx.get("gas_limit").and_then(|v| v.as_u64()).unwrap_or(21000),
            None, None, None, None,
        );

        match tx.get("tx_type").and_then(|v| v.as_str()) {
            Some("eip1559") => {
                req.max_fee_per_gas = tx["max_fee_per_gas"].as_str()
                    .and_then(|s| s.parse().ok());
                req.max_priority_fee_per_gas = tx["max_priority_fee_per_gas"].as_str()
                    .and_then(|s| s.parse().ok());
            }
            _ => {
                req.gas_price = tx.get("gas_price")
                    .and_then(|v| v.as_str())
                    .and_then(|s| s.parse().ok());
            }
        }

        if let Some(d) = tx.get("data").and_then(|v| v.as_str()) {
            req.data = Some(d.to_string());
        }

        Ok(req)
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// TransactionSigner — подпись транзакций
// ─────────────────────────────────────────────────────────────────────────────

/// Подпись ETH транзакций приватным ключом (офлайн).
#[pyclass(module = "coldvault_core")]
pub struct TransactionSigner;

#[pymethods]
impl TransactionSigner {
    #[new]
    pub fn new() -> Self { TransactionSigner }

    /// Подписывает транзакцию, возвращает raw signed TX (0x...).
    #[staticmethod]
    pub fn sign_transaction(
        private_key: &[u8],
        tx_request: &TransactionRequest,
    ) -> PyResult<String> {
        tx_request.validate()?;

        let raw = if tx_request.max_fee_per_gas.is_some() {
            sign_eip1559(private_key, tx_request)?
        } else {
            sign_legacy(private_key, tx_request)?
        };

        Ok(format!("0x{}", hex::encode(raw)))
    }

    /// Подписывает произвольное сообщение (EIP-191).
    /// Возвращает dict с полями: message, signature, v, r, s.
    #[staticmethod]
    pub fn sign_message(private_key: &[u8], message: &str) -> PyResult<std::collections::HashMap<String, String>> {
        // EIP-191 prefix
        let prefixed = format!("\x19Ethereum Signed Message:\n{}{}", message.len(), message);
        let hash = keccak256(prefixed.as_bytes());

        let signing_key = SigningKey::from_slice(private_key)
            .map_err(|e| PyValueError::new_err(format!("Невалидный ключ: {e}")))?;

        let (sig, recid) = signing_key
            .sign_prehash_recoverable(&hash)
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка подписи: {e}")))?;

        let sig_bytes = sig.to_bytes();
        let r = &sig_bytes[..32];
        let s = &sig_bytes[32..];
        let v = 27u8 + recid.to_byte();

        let mut map = std::collections::HashMap::new();
        map.insert("message".into(), message.to_string());
        map.insert("signature".into(), hex::encode(sig_bytes));
        map.insert("v".into(), v.to_string());
        map.insert("r".into(), format!("0x{}", hex::encode(r)));
        map.insert("s".into(), format!("0x{}", hex::encode(s)));
        Ok(map)
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Приватные функции
// ─────────────────────────────────────────────────────────────────────────────

/// keccak256 хэш произвольных байт.
fn keccak256(data: &[u8]) -> [u8; 32] {
    let mut hasher = Keccak::v256();
    let mut out = [0u8; 32];
    hasher.update(data);
    hasher.finalize(&mut out);
    out
}

/// Валидирует Ethereum адрес (hex, 20 байт).
fn validate_eth_address(addr: &str) -> PyResult<()> {
    let hex_part = addr.trim_start_matches("0x").trim_start_matches("0X");
    if hex_part.len() != 40 {
        return Err(PyValueError::new_err(format!("Невалидный ETH-адрес: {addr}")));
    }
    if !hex_part.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err(PyValueError::new_err(format!("Невалидный ETH-адрес (не hex): {addr}")));
    }
    Ok(())
}

/// RLP-кодирование u128 как big-endian без ведущих нулей.
fn rlp_encode_u128(stream: &mut RlpStream, v: u128) {
    if v == 0 {
        stream.append(&0u8);
    } else {
        let bytes = v.to_be_bytes();
        let trimmed: &[u8] = bytes.as_ref();
        let start = trimmed.iter().position(|&b| b != 0).unwrap_or(15);
        stream.append(&trimmed[start..].to_vec());
    }
}

/// Подпись EIP-1559 транзакции (type 2).
fn sign_eip1559(private_key: &[u8], tx: &TransactionRequest) -> PyResult<Vec<u8>> {
    let max_fee = tx.max_fee_per_gas.unwrap();
    let priority = tx.max_priority_fee_per_gas.unwrap();
    let to_bytes = hex::decode(tx.to.trim_start_matches("0x").trim_start_matches("0X"))
        .map_err(|_| PyValueError::new_err("Невалидный адрес получателя"))?;
    let data_bytes = parse_data_field(&tx.data)?;

    // EIP-1559: [chain_id, nonce, max_priority_fee, max_fee, gas_limit, to, value, data, access_list]
    let mut stream = RlpStream::new();
    stream.begin_unbounded_list();
    stream.append(&tx.chain_id);
    stream.append(&tx.nonce);
    rlp_encode_u128(&mut stream, priority);
    rlp_encode_u128(&mut stream, max_fee);
    stream.append(&tx.gas_limit);
    stream.append(&to_bytes);
    rlp_encode_u128(&mut stream, tx.value_wei);
    stream.append(&data_bytes);
    stream.begin_list(0); // access_list пустой
    stream.finalize_unbounded_list();

    let rlp_encoded = stream.out().to_vec();
    // Prefix: 0x02 для EIP-1559
    let mut to_hash = vec![0x02u8];
    to_hash.extend_from_slice(&rlp_encoded);
    let hash = keccak256(&to_hash);

    let (sig_bytes, recid) = sign_hash(private_key, &hash)?;

    // Финальная сериализация: 0x02 ++ RLP([chain_id, nonce, ..., v, r, s])
    let mut final_stream = RlpStream::new();
    final_stream.begin_unbounded_list();
    final_stream.append(&tx.chain_id);
    final_stream.append(&tx.nonce);
    rlp_encode_u128(&mut final_stream, priority);
    rlp_encode_u128(&mut final_stream, max_fee);
    final_stream.append(&tx.gas_limit);
    final_stream.append(&to_bytes);
    rlp_encode_u128(&mut final_stream, tx.value_wei);
    final_stream.append(&data_bytes);
    final_stream.begin_list(0);
    final_stream.append(&recid.to_byte());
    final_stream.append(&sig_bytes[..32].to_vec());
    final_stream.append(&sig_bytes[32..].to_vec());
    final_stream.finalize_unbounded_list();

    let mut result = vec![0x02u8];
    result.extend_from_slice(&final_stream.out());
    Ok(result)
}

/// Подпись Legacy транзакции (EIP-155).
fn sign_legacy(private_key: &[u8], tx: &TransactionRequest) -> PyResult<Vec<u8>> {
    let gas_price = tx.gas_price.unwrap();
    let to_bytes = hex::decode(tx.to.trim_start_matches("0x").trim_start_matches("0X"))
        .map_err(|_| PyValueError::new_err("Невалидный адрес получателя"))?;
    let data_bytes = parse_data_field(&tx.data)?;

    // EIP-155: [nonce, gasPrice, gasLimit, to, value, data, chainId, 0, 0]
    let mut stream = RlpStream::new();
    stream.begin_unbounded_list();
    stream.append(&tx.nonce);
    rlp_encode_u128(&mut stream, gas_price);
    stream.append(&tx.gas_limit);
    stream.append(&to_bytes);
    rlp_encode_u128(&mut stream, tx.value_wei);
    stream.append(&data_bytes);
    stream.append(&tx.chain_id);
    stream.append(&0u8);
    stream.append(&0u8);
    stream.finalize_unbounded_list();

    let hash = keccak256(&stream.out());
    let (sig_bytes, recid) = sign_hash(private_key, &hash)?;

    // v = chain_id * 2 + 35 + recid (EIP-155)
    let v = tx.chain_id * 2 + 35 + recid.to_byte() as u64;

    let mut final_stream = RlpStream::new();
    final_stream.begin_unbounded_list();
    final_stream.append(&tx.nonce);
    rlp_encode_u128(&mut final_stream, gas_price);
    final_stream.append(&tx.gas_limit);
    final_stream.append(&to_bytes);
    rlp_encode_u128(&mut final_stream, tx.value_wei);
    final_stream.append(&data_bytes);
    final_stream.append(&v);
    final_stream.append(&sig_bytes[..32].to_vec());
    final_stream.append(&sig_bytes[32..].to_vec());
    final_stream.finalize_unbounded_list();

    Ok(final_stream.out().to_vec())
}

/// Подписывает 32-байтовый хэш и возвращает (sig_bytes[64], RecoveryId).
fn sign_hash(private_key: &[u8], hash: &[u8; 32]) -> PyResult<(Vec<u8>, RecoveryId)> {
    let signing_key = SigningKey::from_slice(private_key)
        .map_err(|e| PyValueError::new_err(format!("Невалидный ключ: {e}")))?;
    let (sig, recid) = signing_key
        .sign_prehash_recoverable(hash)
        .map_err(|e| PyRuntimeError::new_err(format!("Ошибка подписи: {e}")))?;
    Ok((sig.to_bytes().to_vec(), recid))
}

/// Парсит опциональное поле data из hex-строки в bytes.
fn parse_data_field(data: &Option<String>) -> PyResult<Vec<u8>> {
    match data {
        None => Ok(vec![]),
        Some(d) => {
            let hex_part = d.trim_start_matches("0x").trim_start_matches("0X");
            if hex_part.is_empty() {
                return Ok(vec![]);
            }
            hex::decode(hex_part).map_err(|_| PyValueError::new_err("Невалидный hex в поле data"))
        }
    }
}
