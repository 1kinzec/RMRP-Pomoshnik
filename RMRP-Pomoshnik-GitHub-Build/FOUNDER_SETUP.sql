-- Однократная настройка Основателя.
-- Выполнять в Supabase SQL Editor после регистрации аккаунта.
-- ЗАМЕНИТЕ EMAIL на email аккаунта Основателя.

update public.profiles
set role = 'FOUNDER',
    premium = true,
    status = 'ACTIVE',
    display_name = coalesce(nullif(display_name, ''), username),
    updated_at = now()
where id = (
  select id from auth.users where lower(email) = lower('EMAIL_ОСНОВАТЕЛЯ') limit 1
);

-- Проверка:
select id, username, display_name, role, premium, status
from public.profiles
where role = 'FOUNDER';
