use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum NetworkType {
    Ethereum,
    Polygon,
    BSC,
    Arbitrum,
    Optimism,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Network {
    pub id: String,
    pub name: String,
    pub network_type: NetworkType,
    pub chain_id: u64,
    pub rpc_url: String,
    pub explorer_url: String,
    pub currency_symbol: String,
    pub currency_decimals: u8,
}

impl Network {
    pub fn ethereum_mainnet() -> Self {
        Self {
            id: "ethereum".to_string(),
            name: "Ethereum Mainnet".to_string(),
            network_type: NetworkType::Ethereum,
            chain_id: 1,
            rpc_url: "https://eth.llamarpc.com".to_string(),
            explorer_url: "https://etherscan.io".to_string(),
            currency_symbol: "ETH".to_string(),
            currency_decimals: 18,
        }
    }

    pub fn polygon_mainnet() -> Self {
        Self {
            id: "polygon".to_string(),
            name: "Polygon Mainnet".to_string(),
            network_type: NetworkType::Polygon,
            chain_id: 137,
            rpc_url: "https://polygon-rpc.com".to_string(),
            explorer_url: "https://polygonscan.com".to_string(),
            currency_symbol: "MATIC".to_string(),
            currency_decimals: 18,
        }
    }

    pub fn bsc_mainnet() -> Self {
        Self {
            id: "bsc".to_string(),
            name: "BNB Smart Chain".to_string(),
            network_type: NetworkType::BSC,
            chain_id: 56,
            rpc_url: "https://bsc-dataseed.binance.org".to_string(),
            explorer_url: "https://bscscan.com".to_string(),
            currency_symbol: "BNB".to_string(),
            currency_decimals: 18,
        }
    }

    pub fn arbitrum_mainnet() -> Self {
        Self {
            id: "arbitrum".to_string(),
            name: "Arbitrum One".to_string(),
            network_type: NetworkType::Arbitrum,
            chain_id: 42161,
            rpc_url: "https://arb1.arbitrum.io/rpc".to_string(),
            explorer_url: "https://arbiscan.io".to_string(),
            currency_symbol: "ETH".to_string(),
            currency_decimals: 18,
        }
    }

    pub fn optimism_mainnet() -> Self {
        Self {
            id: "optimism".to_string(),
            name: "Optimism".to_string(),
            network_type: NetworkType::Optimism,
            chain_id: 10,
            rpc_url: "https://mainnet.optimism.io".to_string(),
            explorer_url: "https://optimistic.etherscan.io".to_string(),
            currency_symbol: "ETH".to_string(),
            currency_decimals: 18,
        }
    }

    pub fn get_all_networks() -> Vec<Network> {
        vec![
            Self::ethereum_mainnet(),
            Self::polygon_mainnet(),
            Self::bsc_mainnet(),
            Self::arbitrum_mainnet(),
            Self::optimism_mainnet(),
        ]
    }

    pub fn get_by_id(id: &str) -> Option<Network> {
        Self::get_all_networks()
            .into_iter()
            .find(|n| n.id == id)
    }
}
