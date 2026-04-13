use serde_json;
use reqwest;

pub async fn get_balance(rpc_url: &str, address: &str) -> Result<String, String> {
    let client = reqwest::Client::new();
    
    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1,
    });
    
    let response = client.post(rpc_url)
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    if let Some(error) = result.get("error") {
        return Err(error.to_string());
    }
    
    let balance_hex = result.get("result")
        .and_then(|v| v.as_str())
        .ok_or("Invalid response format")?;
    
    let balance_wei = u64::from_str_radix(&balance_hex[2..], 16)
        .map_err(|e| format!("Failed to parse balance: {}", e))?;
    
    let balance_eth = balance_wei as f64 / 1e18;
    
    Ok(format!("{:.8}", balance_eth))
}

pub async fn get_nonce(rpc_url: &str, address: &str) -> Result<u64, String> {
    let client = reqwest::Client::new();
    
    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "eth_getTransactionCount",
        "params": [address, "latest"],
        "id": 1,
    });
    
    let response = client.post(rpc_url)
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    if let Some(error) = result.get("error") {
        return Err(error.to_string());
    }
    
    let nonce_hex = result.get("result")
        .and_then(|v| v.as_str())
        .ok_or("Invalid response format")?;
    
    let nonce = u64::from_str_radix(&nonce_hex[2..], 16)
        .map_err(|e| format!("Failed to parse nonce: {}", e))?;
    
    Ok(nonce)
}

pub async fn fetch_eth_price_rub() -> Result<f64, String> {
    let client = reqwest::Client::new();
    
    let response = client.get("https://api.coingecko.com/api/v3/simple/price")
        .query(&[
            ("ids", "ethereum"),
            ("vs_currencies", "rub"),
        ])
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    let price = result.get("ethereum")
        .and_then(|v| v.get("rub"))
        .and_then(|v| v.as_f64())
        .ok_or("Failed to parse price")?;
    
    Ok(price)
}

pub async fn get_transaction_history(rpc_url: &str, address: &str) -> Result<Vec<serde_json::Value>, String> {
    // Use Etherscan API for transaction history
    let api_key = ""; // In production, use environment variable
    let etherscan_url = format!(
        "https://api.etherscan.io/api?module=account&action=txlist&address={}&startblock=0&endblock=99999999&page=1&offset=50&sort=desc&apikey={}",
        address, api_key
    );
    
    let client = reqwest::Client::new();
    
    let response = client.get(&etherscan_url)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    if result.get("status").and_then(|v| v.as_str()) != Some("1") {
        return Err(result.get("message").and_then(|v| v.as_str()).unwrap_or("Unknown error").to_string());
    }
    
    let txs = result.get("result")
        .and_then(|v| v.as_array())
        .ok_or("Invalid response format")?;
    
    let mut transactions = vec![];
    
    for tx in txs {
        let tx_hash = tx.get("hash").and_then(|v| v.as_str()).unwrap_or("");
        let from = tx.get("from").and_then(|v| v.as_str()).unwrap_or("");
        let to = tx.get("to").and_then(|v| v.as_str()).unwrap_or("");
        let value = tx.get("value").and_then(|v| v.as_str()).unwrap_or("0");
        let timestamp = tx.get("timeStamp").and_then(|v| v.as_str()).unwrap_or("0");
        let tx_type = if from.to_lowercase() == address.to_lowercase() {
            "outgoing"
        } else {
            "incoming"
        };
        
        let value_eth = value.parse::<f64>().unwrap_or(0.0) / 1e18;
        
        transactions.push(serde_json::json!({
            "hash": tx_hash,
            "from": from,
            "to": to,
            "value": value,
            "nonce": tx.get("nonce").and_then(|v| v.as_str()).unwrap_or("0"),
            "gasLimit": tx.get("gas").and_then(|v| v.as_str()).unwrap_or("21000"),
            "timestamp": timestamp,
            "status": if tx.get("isError").and_then(|v| v.as_str()) == Some("0") {
                "confirmed"
            } else {
                "failed"
            },
            "type": tx_type,
        }));
    }
    
    Ok(transactions)
}

pub async fn fetch_gas_settings(rpc_url: &str) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    
    // Get base fee from latest block
    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "eth_gasPrice",
        "params": [],
        "id": 1,
    });
    
    let response = client.post(rpc_url)
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    if let Some(error) = result.get("error") {
        return Err(error.to_string());
    }
    
    let gas_price_hex = result.get("result")
        .and_then(|v| v.as_str())
        .ok_or("Invalid response format")?;
    
    let gas_price_wei = u64::from_str_radix(&gas_price_hex[2..], 16)
        .map_err(|e| format!("Failed to parse gas price: {}", e))?;
    
    let gas_price_gwei = gas_price_wei as f64 / 1e9;
    
    Ok(serde_json::json!({
        "maxFeePerGas": gas_price_gwei,
        "maxPriorityFeePerGas": 2.0,
    }))
}

pub async fn broadcast_transaction(rpc_url: &str, raw_tx: &str) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    
    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "eth_sendRawTransaction",
        "params": [raw_tx],
        "id": 1,
    });
    
    let response = client.post(rpc_url)
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    if let Some(error) = result.get("error") {
        return Err(error.to_string());
    }
    
    let tx_hash = result.get("result")
        .and_then(|v| v.as_str())
        .ok_or("Invalid response format")?;
    
    Ok(serde_json::json!({
        "hash": tx_hash,
    }))
}
