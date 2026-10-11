-- RMRP Помощник 2.3: админ и основатель могут удалять и править контент из приложения.
-- Выполнить в Supabase → SQL Editor. Безопасно запускать повторно.

-- Жалобы: удаление только админом/основателем (модератор может менять статус, но не удалять)
drop policy if exists "reports_admin_delete" on public.reports;
create policy "reports_admin_delete" on public.reports for delete to authenticated
using (public.is_admin_or_founder());

-- Законы, статьи, версии, тесты, вопросы: полный доступ админу/основателю (на случай, если политик нет)
do $$
declare t text;
begin
  foreach t in array array['laws','law_articles','law_versions','tests','questions'] loop
    execute format('drop policy if exists %I on public.%I', t || '_admin_write', t);
    execute format('create policy %I on public.%I for all to authenticated using (public.is_admin_or_founder()) with check (public.is_admin_or_founder())', t || '_admin_write', t);
  end loop;
end $$;

-- Результаты тестов и ответы удаляются каскадом вместе с тестом (уже настроено внешними ключами).
-- Журнал: админ может писать записи о своих действиях (если политики нет — приложение просто пропустит запись).
