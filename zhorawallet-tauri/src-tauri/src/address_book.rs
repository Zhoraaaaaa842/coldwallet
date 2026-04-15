use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contact {
    pub id: String,
    pub name: String,
    pub address: String,
    pub note: Option<String>,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AddressBook {
    pub contacts: Vec<Contact>,
}

impl AddressBook {
    pub fn new() -> Self {
        Self {
            contacts: Vec::new(),
        }
    }

    pub fn load_from_file(path: &str) -> Result<Self, String> {
        if !Path::new(path).exists() {
            return Ok(Self::new());
        }

        let data = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read address book: {}", e))?;

        let book: AddressBook = serde_json::from_str(&data)
            .map_err(|e| format!("Failed to parse address book: {}", e))?;

        Ok(book)
    }

    pub fn save_to_file(&self, path: &str) -> Result<(), String> {
        let data = serde_json::to_string_pretty(self)
            .map_err(|e| format!("Failed to serialize address book: {}", e))?;

        if let Some(parent) = Path::new(path).parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directory: {}", e))?;
        }

        fs::write(path, data)
            .map_err(|e| format!("Failed to write address book: {}", e))?;

        Ok(())
    }

    pub fn add_contact(&mut self, contact: Contact) -> Result<(), String> {
        if self.contacts.iter().any(|c| c.id == contact.id) {
            return Err("Contact with this ID already exists".to_string());
        }

        if self.contacts.iter().any(|c| c.address.to_lowercase() == contact.address.to_lowercase()) {
            return Err("Contact with this address already exists".to_string());
        }

        self.contacts.push(contact);
        Ok(())
    }

    pub fn update_contact(&mut self, id: &str, name: String, address: String, note: Option<String>) -> Result<(), String> {
        // First check if address is already used by another contact
        if self.contacts.iter().any(|c| c.id != id && c.address.to_lowercase() == address.to_lowercase()) {
            return Err("Another contact with this address already exists".to_string());
        }

        // Then update the contact
        let contact = self.contacts.iter_mut()
            .find(|c| c.id == id)
            .ok_or("Contact not found")?;

        contact.name = name;
        contact.address = address;
        contact.note = note;
        contact.updated_at = chrono::Utc::now().timestamp();

        Ok(())
    }

    pub fn delete_contact(&mut self, id: &str) -> Result<(), String> {
        let index = self.contacts.iter()
            .position(|c| c.id == id)
            .ok_or("Contact not found")?;

        self.contacts.remove(index);
        Ok(())
    }

    pub fn get_contact(&self, id: &str) -> Option<&Contact> {
        self.contacts.iter().find(|c| c.id == id)
    }

    pub fn get_all_contacts(&self) -> Vec<Contact> {
        self.contacts.clone()
    }

    pub fn search_contacts(&self, query: &str) -> Vec<Contact> {
        let query_lower = query.to_lowercase();
        self.contacts.iter()
            .filter(|c| {
                c.name.to_lowercase().contains(&query_lower) ||
                c.address.to_lowercase().contains(&query_lower) ||
                c.note.as_ref().map_or(false, |n| n.to_lowercase().contains(&query_lower))
            })
            .cloned()
            .collect()
    }
}
