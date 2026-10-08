-- RMRP Помощник 1.5.0
-- Регистрирует официальные источники законодательства.
-- Полные статьи загружаются кнопкой «Синхронизировать RMRP» внутри приложения.

insert into public.laws (name, short_name, law_number, description, source_url, is_active) values
('Федеральный закон «О государственной службе» № 54-ФЗ','ФЗ «О госслужбе»','54-ФЗ','Актуальная редакция RMRP.','https://forum.rmrp.ru/threads/federalnyj-zakon-o-gosudarstvennoj-sluzhbe-no-54-fz.25075/',true),
('Уголовный Кодекс Российской Федерации','УК РФ','УК РФ','Актуальная редакция RMRP.','https://forum.rmrp.ru/threads/ugolovnyj-kodeks-rossijskoj-federacii.58209/',true),
('Кодекс об административных правонарушениях Российской Федерации','КоАП РФ','КоАП РФ','Актуальная редакция RMRP.','https://forum.rmrp.ru/threads/kodeks-ob-administrativnyx-pravonarushenijax-rossijskoj-federacii.58229/',true),
('Процессуальный Кодекс Российской Федерации','Процессуальный кодекс','ПК РФ','Актуальная редакция RMRP.','https://forum.rmrp.ru/threads/processualnyj-kodeks-rossijskoj-federacii.58424/',true),
('Федеральный закон «О полиции» № 74-ФЗ','ФЗ «О полиции»','74-ФЗ','Актуальная редакция RMRP.','https://forum.rmrp.ru/threads/federalnyj-zakon-o-policii-no-74-fz.25074/',true),
('Федеральный закон «О Федеральной службе войск национальной гвардии» № 18-ФЗ','ФЗ «О ФСВНГ»','18-ФЗ','Актуальная редакция RMRP.','https://forum.rmrp.ru/threads/federalnyj-zakon-o-federalnoj-sluzhbe-vojsk-nacionalnoj-gvardii-no-18-fz.25071/',true);
