# RMRP Помощник — сборка Windows

Эта версия специально подготовлена для автоматической сборки на Windows через GitHub Actions.

## Что получится
- RMRP_Pomoshnik.exe
- RMRP-Pomoshnik-Setup-1.0.0.exe — обычный установщик Windows

## Как собрать
1. Создайте новый репозиторий на GitHub.
2. Загрузите в него содержимое этой папки.
3. Откройте вкладку Actions.
4. Выберите `Build RMRP Помощник for Windows`.
5. Нажмите `Run workflow`.
6. После завершения откройте результат запуска и скачайте artifact `RMRP-Pomoshnik-Windows`.

Локально Python/PySide6 устанавливать не требуется: приложение использует стандартный tkinter Python.
