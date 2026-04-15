mod commands;
mod crypto;
mod usb;
mod network;
mod state;
mod networks;
mod address_book;
mod transaction_cache;
mod validation;

use tauri::Manager;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::check_usb_status,
            commands::initialize_wallet,
            commands::import_from_mnemonic,
            commands::unlock_wallet,
            commands::get_balance,
            commands::get_nonce,
            commands::fetch_eth_price_rub,
            commands::get_transaction_history,
            commands::fetch_gas_settings,
            commands::create_unsigned_transaction,
            commands::scan_pending_transactions,
            commands::scan_signed_transactions,
            commands::sign_transaction,
            commands::broadcast_transaction,
            commands::save_qr_image,
            commands::decode_qr_from_image,
            commands::get_mnemonic,
            commands::get_all_networks,
            commands::get_current_network,
            commands::switch_network,
            commands::add_contact,
            commands::update_contact,
            commands::delete_contact,
            commands::get_all_contacts,
            commands::search_contacts,
            commands::get_cached_transactions,
            commands::get_balance_summary,
        ])
        .setup(|app| {
            // Initialize app state
            app.manage(state::AppState::default());
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}
