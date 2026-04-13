# Очистка истории Git от чувствительных файлов

Файлы `.claude/`, `.qwen/` и `claude_free.bat` были удалены из текущей версии, но остались в истории Git.

## Способ 1: BFG Repo-Cleaner (Рекомендуется)

1. Скачайте BFG: https://rtyley.github.io/bfg-repo-cleaner/
2. Запустите:
```bash
java -jar bfg.jar --delete-folders .claude --delete-folders .qwen --delete-files claude_free.bat --no-blob-protection
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

## Способ 2: Создать новый репозиторий

Самый простой способ - создать новый репозиторий без истории:

```bash
# Удалить .git
rm -rf .git

# Создать новый репозиторий
git init
git add .
git commit -m "Initial commit: ZhoraWallet - Ethereum Cold Wallet"

# Подключить к GitHub
git remote add origin https://github.com/Zhoraaaaaa842/coldwallet.git
git push -u origin master --force
```

## Текущий статус

- ✅ Файлы удалены из текущей версии
- ✅ Добавлены в .gitignore
- ⚠️ Остались в истории (12 объектов)

Если в файлах не было критичных данных (паролей, ключей), можно оставить как есть.
