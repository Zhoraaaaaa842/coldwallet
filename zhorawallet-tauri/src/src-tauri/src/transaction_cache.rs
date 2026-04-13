use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub hash: String,
    pub from: String,
    pub to: String,
    pub value: String,
    pub value_eth: f64,
    pub gas_used: String,
    pub gas_price: String,
    pub timestamp: i64,
    pub block_number: u64,
    pub status: String,
    pub tx_type: String, // "incoming" or "outgoing"
    pub network_id: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TransactionCache {
    pub address: String,
    pub network_id: String,
    pub transactions: Vec<Transaction>,
    pub last_updated: i64,
}

impl TransactionCache {
    pub fn new(address: String, network_id: String) -> Self {
        Self {
            address,
            network_id,
            transactions: Vec::new(),
            last_updated: 0,
        }
    }

    pub fn load_from_file(path: &str) -> Result<HashMap<String, Self>, String> {
        if !Path::new(path).exists() {
            return Ok(HashMap::new());
        }

        let data = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read cache: {}", e))?;

        let cache: HashMap<String, TransactionCache> = serde_json::from_str(&data)
            .map_err(|e| format!("Failed to parse cache: {}", e))?;

        Ok(cache)
    }

    pub fn save_to_file(cache: &HashMap<String, Self>, path: &str) -> Result<(), String> {
        let data = serde_json::to_string_pretty(cache)
            .map_err(|e| format!("Failed to serialize cache: {}", e))?;

        if let Some(parent) = Path::new(path).parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directory: {}", e))?;
        }

        fs::write(path, data)
            .map_err(|e| format!("Failed to write cache: {}", e))?;

        Ok(())
    }

    pub fn get_cache_key(address: &str, network_id: &str) -> String {
        format!("{}_{}", address.to_lowercase(), network_id)
    }

    pub fn is_stale(&self, max_age_seconds: i64) -> bool {
        let now = chrono::Utc::now().timestamp();
        now - self.last_updated > max_age_seconds
    }

    pub fn update_transactions(&mut self, transactions: Vec<Transaction>) {
        self.transactions = transactions;
        self.last_updated = chrono::Utc::now().timestamp();
    }

    pub fn get_filtered_transactions(
        &self,
        tx_type: Option<&str>,
        limit: Option<usize>,
    ) -> Vec<Transaction> {
        let mut txs = self.transactions.clone();

        if let Some(filter_type) = tx_type {
            txs.retain(|tx| tx.tx_type == filter_type);
        }

        if let Some(limit_count) = limit {
            txs.truncate(limit_count);
        }

        txs
    }

    pub fn get_balance_changes(&self) -> (f64, f64) {
        let mut total_in = 0.0;
        let mut total_out = 0.0;

        for tx in &self.transactions {
            if tx.status == "1" || tx.status == "success" {
                if tx.tx_type == "incoming" {
                    total_in += tx.value_eth;
                } else {
                    total_out += tx.value_eth;
                }
            }
        }

        (total_in, total_out)
    }
}
