mod commands;
mod crypto;
mod usb;
mod network;
mod state;

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
        ])
        .setup(|app| {
            app.manage(state::AppState::default());
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}
